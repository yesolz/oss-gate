"""Bounded, non-executing Yarn Berry inventory. Never resolve registry ranges."""

from collections import deque
from fnmatch import fnmatchcase
from functools import lru_cache
from pathlib import PurePosixPath
import hashlib
import re

import yaml

MAX_NODES = 10000
GROUPS = ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")
NAME = re.compile(r"(?:@[a-z0-9._~-]+/)?[a-z0-9._~-]+\Z")
NUM = r"(?:0|[1-9]\d*)"
PRE = r"(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
VERSION = re.compile(rf"{NUM}\.{NUM}\.{NUM}(?:-{PRE}(?:\.{PRE})*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?\Z")


class LockLoader(yaml.BaseLoader):
    """Strings only, with no tags, aliases, duplicate keys or deep nesting."""

    def __init__(self, stream):
        super().__init__(stream)
        self.depth = self.nodes = 0

    def compose_node(self, parent, index):
        self.depth += 1
        self.nodes += 1
        if self.depth > 16 or self.nodes > 250000 or self.check_event(yaml.AliasEvent):
            raise ValueError("YAML resource limit or alias")
        event = self.peek_event()
        if getattr(event, "anchor", None) or getattr(event, "tag", None):
            raise ValueError("YAML anchors and tags are unsupported")
        try:
            return super().compose_node(parent, index)
        finally:
            self.depth -= 1

    def construct_mapping(self, node, deep=False):
        out = {}
        for key, value in node.value:
            key = self.construct_object(key, deep=deep)
            if not isinstance(key, str) or key in out:
                raise ValueError("duplicate or non-scalar YAML key")
            out[key] = self.construct_object(value, deep=deep)
        return out


def parse(text):
    try:
        data = yaml.load(text, Loader=LockLoader)
    except yaml.YAMLError as exc:
        raise ValueError("invalid Yarn lock YAML") from exc
    if not isinstance(data, dict) or not isinstance(data.get("__metadata"), dict):
        raise ValueError("Yarn Classic or missing Berry metadata")
    if data["__metadata"].get("version") not in {str(n) for n in range(4, 11)}:
        raise ValueError("unsupported Berry lock format version")
    if len(data) > MAX_NODES + 1:
        raise ValueError("too many lock entries")
    entries, descriptors = {}, {}
    for key, value in data.items():
        if key == "__metadata":
            continue
        if not isinstance(value, dict) or not isinstance(value.get("resolution"), str):
            raise ValueError("missing lock resolution")
        locator = value["resolution"]
        if locator in entries and entries[locator] != value:
            raise ValueError("conflicting lock resolutions")
        entries[locator] = value
        for descriptor in key.split(", "):
            if descriptor in descriptors and descriptors[descriptor] != locator:
                raise ValueError("ambiguous lock descriptor")
            descriptors[descriptor] = locator
        for group in GROUPS:
            if group in value and (
                not isinstance(value[group], dict)
                or any(not isinstance(k, str) or not isinstance(v, str) for k, v in value[group].items())
            ):
                raise ValueError("invalid lock dependency map")
    return entries, descriptors


def identity(locator):
    name, sep, reference = locator.rpartition("@")
    if not sep or not NAME.fullmatch(name) or any(p in (".", "..") for p in name.lstrip("@").split("/")):
        return None
    if reference.startswith("npm:") and VERSION.fullmatch(reference[4:]):
        return {"system": "npm", "name": name, "version": reference[4:]}
    return None


def workspace_path(locator):
    name, sep, path = locator.partition("@workspace:")
    if not sep or not NAME.fullmatch(name):
        return None
    p = PurePosixPath(path)
    if not path or p.is_absolute() or ".." in p.parts or "\\" in path:
        raise ValueError("invalid workspace path")
    return p.as_posix()


def matches(path, pattern):
    """Workspace globs: segment-local *, ?, [] and recursive **."""
    parts, patterns = PurePosixPath(path).parts, PurePosixPath(pattern).parts

    @lru_cache(maxsize=None)
    def match(i, j):
        if j == len(patterns):
            return i == len(parts)
        if patterns[j] == "**":
            return match(i, j + 1) or (i < len(parts) and match(i + 1, j))
        return i < len(parts) and fnmatchcase(parts[i], patterns[j]) and match(i + 1, j + 1)

    return match(0, 0)


def analyze(text, manifests, lockfile):
    """Manifests are paths relative to this lock's directory, mapped to JSON objects."""
    entries, descriptors = parse(text)
    gaps, gap_keys, projects, occurrences, unresolved = [], set(), [], [], []

    def gap(code, source=lockfile, **detail):
        item = {"code": code, "source": source, **detail}
        key = (code, source, tuple(sorted(detail.items())))
        if key not in gap_keys:
            gap_keys.add(key)
            gaps.append(item)

    roots = {}
    for locator, entry in entries.items():
        path = workspace_path(locator)
        if path is not None:
            if path in roots:
                raise ValueError("duplicate workspace location")
            roots[path] = locator
        package = identity(locator)
        if package:
            if entry.get("version") != package["version"]:
                gap("lock_version_mismatch", package=package["name"])
            occurrences.append({**package, "lockfile": lockfile, "projects": [], "direct_uses": []})
        elif path is None:
            # Do not persist arbitrary locators: URLs may contain credentials.
            source_id = hashlib.sha256(locator.encode()).hexdigest()
            source = re.match(r"^((?:@[a-z0-9._~-]+/)?[a-z0-9._~-]+)@([a-zA-Z][a-zA-Z0-9+.-]*):", locator)
            detail = {
                "locator_sha256": source_id,
                "dependency": source[1] if source else "unknown",
                "source_type": source[2] if source else "unknown",
            }
            unresolved.append({"lockfile": lockfile, **detail})
            gap("unsupported_dependency_source", **detail)
    if len(roots) > 256:
        raise ValueError("workspace count exceeds analysis limit")
    if "." not in roots:
        gap("root_workspace_missing")
    root_manifest = manifests.get(".", {})
    manager = root_manifest.get("packageManager")
    if manager is not None and (not isinstance(manager, str) or not re.match(r"^yarn@(?:[2-9]|[1-9]\d+)\.", manager)):
        gap("package_manager_mismatch")
    patterns = root_manifest.get("workspaces", [])
    if isinstance(patterns, dict):
        patterns = patterns.get("packages", [])
    if not isinstance(patterns, list) or any(not isinstance(p, str) for p in patterns):
        gap("invalid_workspace_patterns")
        patterns = []
    usable_patterns = []
    for pattern in patterns:
        if (
            len(pattern) > 512
            or pattern.startswith(("!", "/"))
            or any(c in pattern for c in "{}\\")
            or ".." in PurePosixPath(pattern).parts
        ):
            gap("unsupported_workspace_pattern")
        else:
            usable_patterns.append(pattern)
    for path in manifests:
        if path != "." and path not in roots:
            gap("manifest_not_in_lock", path=path)
    for path in roots:
        if path != "." and not any(matches(path, p) for p in usable_patterns):
            gap("workspace_not_declared", path=path)

    def resolve(name, spec):
        exact = descriptors.get(f"{name}@{spec}")
        if exact:
            return exact
        if not re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", spec):
            return descriptors.get(f"{name}@npm:{spec}")
        if spec in ("workspace:*", "workspace:^", "workspace:~"):
            candidates = [loc for loc in roots.values() if loc.split("@workspace:", 1)[0] == name]
            if len(candidates) == 1:
                return candidates[0]
        return None

    adjacency = {}
    for locator, entry in entries.items():
        edges = []
        for name, spec in entry.get("dependencies", {}).items():
            target = resolve(name, spec)
            if target is None:
                gap("unresolved_lock_edge")
            else:
                edges.append(target)
        adjacency[locator] = edges
        if entry.get("peerDependencies"):
            gap("peer_bindings_unverified")

    by_locator = {loc: row for loc, row in zip([loc for loc in entries if identity(loc)], occurrences)}
    visits = 0
    for path, locator in sorted(roots.items()):
        manifest = manifests.get(path)
        source = str(PurePosixPath(lockfile).parent / path / "package.json")
        project = {"path": source, "lockfile": lockfile, "direct_dependencies": []}
        projects.append(project)
        if manifest is None:
            gap("workspace_manifest_missing", source)
            continue
        if manifest.get("name") and manifest["name"] != locator.split("@workspace:", 1)[0]:
            gap("workspace_name_mismatch", source)
        declared_names = set()
        for group in GROUPS:
            declarations = manifest.get(group, {})
            if not isinstance(declarations, dict):
                gap("invalid_manifest_dependencies", source)
                continue
            for name, spec in sorted(declarations.items()):
                if not isinstance(name, str) or not NAME.fullmatch(name) or not isinstance(spec, str):
                    gap("invalid_manifest_dependency", source)
                    continue
                if group == "peerDependencies":
                    gap("peer_bindings_unverified", source)
                    continue
                declared_names.add(name)
                target = resolve(name, spec)
                # Root lock dependency edges are an independent freshness check.
                locked_spec = entries[locator].get("dependencies", {}).get(name)
                locked_target = resolve(name, locked_spec) if isinstance(locked_spec, str) else None
                if target is None or target != locked_target:
                    gap("manifest_lock_mismatch", source, package=name, group=group)
                    continue
                package = identity(target)
                if package:
                    project["direct_dependencies"].append({**package, "group": group, "declared_name": name})
                    by_locator[target]["direct_uses"].append({"project": source, "group": group, "declared_name": name})
        if set(entries[locator].get("dependencies", {})) - declared_names:
            gap("stale_workspace_dependencies", source)
        visited, queue = set(), deque([locator])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visits += 1
            if visits > 100000:
                raise ValueError("workspace graph traversal limit")
            visited.add(current)
            if current in by_locator:
                by_locator[current]["projects"].append(source)
            queue.extend(adjacency.get(current, []))
    for row in occurrences:
        if not row["projects"]:
            gap("unattributed_lock_entry", package=row["name"])
    return {
        "projects": projects,
        "packages": occurrences,
        "coverage_gaps": gaps,
        "unresolved": unresolved,
        "lock_entries": len(entries),
        "workspace_count": len(roots),
    }
