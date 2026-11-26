"""Read Cargo lock identities and project attribution without invoking Cargo."""

from collections import deque
import hashlib
from pathlib import PurePosixPath
import re

import tomli

from .gomod import local_path
from .yarn import VERSION, matches

NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_-]*\Z")
CRATES_IO = {"registry+https://github.com/rust-lang/crates.io-index", "sparse+https://index.crates.io/"}
GROUPS = ("dependencies", "dev-dependencies", "build-dependencies")


def parse(text):
    data = tomli.loads(text)
    queue, count = [(data, 0)], 0
    while queue:
        item, depth = queue.pop()
        count += 1
        if depth > 32 or count > 250000:
            raise ValueError("TOML resource limit")
        if isinstance(item, dict):
            queue.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            queue.extend((v, depth + 1) for v in item)
    return data


def dependencies(manifest):
    """Include every target, optional, build and development declaration."""
    sections = [("", manifest)]
    targets = manifest.get("target", {})
    if not isinstance(targets, dict):
        raise ValueError("invalid target table")
    sections.extend(("target:" + target + "/", table) for target, table in targets.items())
    for prefix, section in sections:
        if not isinstance(section, dict):
            raise ValueError("invalid dependency table")
        for group in GROUPS:
            values = section.get(group, {})
            if not isinstance(values, dict):
                raise ValueError("invalid dependency table")
            for alias, value in values.items():
                if not NAME.fullmatch(alias) or not isinstance(value, (str, dict)):
                    raise ValueError("invalid dependency")
                yield prefix + group, alias, {"version": value} if isinstance(value, str) else value


def requirement_matches(requirement, value):
    """Verify common Cargo requirements; unknown syntax stays unknown, never true."""
    if not isinstance(requirement, str) or len(requirement) > 512:
        return None
    # Prerelease matching and advanced syntax need Cargo's resolver.
    if "-" in value or "+" in value:
        return None
    actual = tuple(int(p) for p in value.split("."))
    outcomes = []
    for term in requirement.split(","):
        m = re.fullmatch(r"\s*(\^|~|>=|<=|>|<|=)?\s*(\d+|\*|x|X)(?:\.(\d+|\*|x|X))?(?:\.(\d+|\*|x|X))?\s*", term)
        if not m:
            return None
        op, *parts = m.groups()
        nums = []
        wildcard = False
        for part in parts:
            if part is None:
                break
            if part in ("*", "x", "X"):
                wildcard = True
            elif wildcard:
                return None
            else:
                nums.append(int(part))
        if wildcard:
            if op or not nums:
                outcomes.append(not op)
            else:
                outcomes.append(actual[: len(nums)] == tuple(nums))
            continue
        lower = tuple(nums + [0] * (3 - len(nums)))
        if op in (">=", "<=", ">", "<"):
            if len(nums) != 3:
                return None
            outcomes.append(
                {">=": actual >= lower, "<=": actual <= lower, ">": actual > lower, "<": actual < lower}[op]
            )
        elif op == "=":
            outcomes.append(actual[: len(nums)] == tuple(nums))
        else:
            if not nums:
                return None
            if op == "~":
                pivot = 0 if len(nums) == 1 else 1
            else:
                pivot = next((i for i, n in enumerate(nums) if n), len(nums) - 1)
            upper = list(lower)
            upper[pivot] += 1
            upper[pivot + 1 :] = [0] * (2 - pivot)
            outcomes.append(lower <= actual < tuple(upper))
    return all(outcomes)


def analyze(contents):
    projects, packages, gaps, unresolved, statuses = [], [], [], [], {}
    manifests, locks = {}, {}

    def gap(code, source):
        gaps.append({"code": code, "source": source})

    for path, text in sorted(contents.items()):
        name = PurePosixPath(path).name
        if name not in {"Cargo.toml", "Cargo.lock"}:
            continue
        try:
            data = parse(text)
            (locks if name == "Cargo.lock" else manifests)[path] = data
            statuses[path] = "parsed"
        except (ValueError, TypeError, RecursionError):
            statuses[path] = "invalid_or_unsupported"
            gap("cargo_manifest_invalid", path)

    used = set()
    for lockfile, lock in locks.items():
        try:
            result = analyze_lock(lockfile, lock, manifests)
            projects.extend(result["projects"])
            packages.extend(result["packages"])
            gaps.extend(result["coverage_gaps"])
            unresolved.extend(result["unresolved"])
            used.update(result["used_manifests"])
        except (ValueError, TypeError, RecursionError):
            statuses[lockfile] = "invalid_or_unsupported"
            gap("cargo_lock_invalid", lockfile)
    for path in manifests.keys() - used:
        statuses[path] = "unresolved"
        gap("cargo_manifest_unassigned", path)
    return {
        "projects": projects,
        "packages": packages,
        "coverage_gaps": gaps,
        "unresolved": unresolved,
        "statuses": statuses,
    }


def analyze_lock(lockfile, lock, manifests):
    gaps, unresolved, projects = [], [], []

    def gap(code, source=lockfile):
        gaps.append({"code": code, "source": source})

    if type(lock.get("version")) is not int or lock["version"] not in (3, 4):
        raise ValueError("unsupported Cargo lock version")
    rows = lock.get("package")
    if not isinstance(rows, list) or not rows or len(rows) > 10000:
        raise ValueError("invalid or oversized Cargo lock")
    nodes, by_name = {}, {}
    for row in rows:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("name"), str)
            or not NAME.fullmatch(row["name"])
            or not isinstance(row.get("version"), str)
            or not VERSION.fullmatch(row["version"])
            or not isinstance(row.get("source", ""), str)
        ):
            raise ValueError("invalid Cargo package")
        key = (row["name"], row["version"], row.get("source", ""))
        if key in nodes:
            raise ValueError("duplicate Cargo package")
        nodes[key] = row
        by_name.setdefault(key[0], []).append(key)
    packages = {}
    for key, row in nodes.items():
        name, version, source = key
        if source in CRATES_IO and "replace" not in row:
            packages[key] = {
                "system": "cargo",
                "name": name,
                "version": version,
                "lockfile": lockfile,
                "projects": [],
                "direct_uses": [],
                "basis": "locked",
            }
        elif source or "replace" in row:
            gap("cargo_source_unverified")
            unresolved.append(
                {
                    "source": lockfile,
                    "dependency": name,
                    "source_type": "git" if source.startswith("git+") else "alternate_registry_or_replacement",
                    "locator_sha256": hashlib.sha256(source.encode()).hexdigest(),
                }
            )

    edges = {}
    for key, row in nodes.items():
        deps = row.get("dependencies", [])
        if not isinstance(deps, list) or len(deps) > 10000:
            raise ValueError("invalid lock dependencies")
        edges[key] = []
        for entry in deps:
            if not isinstance(entry, str):
                raise ValueError("invalid lock edge")
            match = re.fullmatch(r"([A-Za-z0-9_-]+)(?: ([^\s()]+))?(?: \(([^\r\n]+)\))?", entry)
            if not match:
                gap("unresolved_lock_edge")
                continue
            name, version, source = match.groups()
            candidates = [
                k for k in by_name.get(name, []) if (not version or k[1] == version) and (not source or k[2] == source)
            ]
            if len(candidates) != 1:
                gap("unresolved_lock_edge")
            else:
                edges[key].append(candidates[0])

    rootpath = str(PurePosixPath(lockfile).with_name("Cargo.toml"))
    root = manifests.get(rootpath)
    if root is None:
        gap("cargo_root_manifest_missing")
        return {
            "projects": [],
            "packages": list(packages.values()),
            "coverage_gaps": gaps,
            "unresolved": unresolved,
            "used_manifests": [],
        }
    workspace = root.get("workspace", {})
    if not isinstance(workspace, dict) or not isinstance(workspace.get("package", {}), dict):
        raise ValueError("invalid Cargo workspace")
    members = {rootpath}
    base = PurePosixPath(rootpath).parent
    patterns, excludes = workspace.get("members", []), workspace.get("exclude", [])
    for values in (patterns, excludes):
        if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
            raise ValueError("invalid Cargo workspace patterns")
    if any(not local_path(rootpath, p, "Cargo.toml") or any(c in p for c in "!{}\\") for p in excludes):
        gap("unsupported_workspace_pattern", rootpath)
    for pattern in patterns:
        if (
            not local_path(rootpath, pattern, "Cargo.toml")
            or any(c in pattern for c in "!{}\\")
            or ".." in PurePosixPath(pattern).parts
        ):
            gap("unsupported_workspace_pattern", rootpath)
            continue
        found = []
        for path in manifests:
            parent = PurePosixPath(path).parent
            if not parent.is_relative_to(base):
                continue
            relative = parent.relative_to(base).as_posix()
            if matches(relative, pattern) and not any(matches(relative, p) for p in excludes):
                found.append(path)
        if not found:
            gap("cargo_workspace_member_missing", rootpath)
        members.update(found)

    inherited = workspace.get("dependencies", {})
    if not isinstance(inherited, dict):
        raise ValueError("invalid inherited dependencies")

    def declarations(path):
        for group, alias, spec in dependencies(manifests[path]):
            origin = path
            if "workspace" in spec and spec["workspace"] is not True:
                gap("invalid_manifest_dependency", path)
                continue
            if spec.get("workspace") is True:
                base_spec = inherited.get(alias)
                if isinstance(base_spec, str):
                    base_spec = {"version": base_spec}
                if not isinstance(base_spec, dict):
                    gap("cargo_inheritance_unresolved", path)
                    continue
                spec, origin = (
                    {**base_spec, **{k: v for k, v in spec.items() if k in {"features", "optional"}}},
                    rootpath,
                )
            source_fields = {"path", "git", "registry"} & spec.keys()
            if (
                (not source_fields and "version" not in spec)
                or len(source_fields) > 1
                or any(
                    not isinstance(spec[k], str)
                    for k in {"version", "path", "git", "registry", "package"} & spec.keys()
                )
                or any(
                    type(spec[k]) is not bool
                    for k in {"optional", "default-features", "default_features"} & spec.keys()
                )
                or (
                    "features" in spec
                    and (
                        not isinstance(spec["features"], list) or any(not isinstance(f, str) for f in spec["features"])
                    )
                )
            ):
                gap("invalid_manifest_dependency", path)
                continue
            yield group, alias, spec, origin

    # Cargo implicitly includes in-tree path dependencies in a workspace.
    pending, checked = deque(sorted(members)), set()
    while pending:
        path = pending.popleft()
        if path in checked:
            continue
        checked.add(path)
        if len(checked) > 256:
            raise ValueError("Cargo workspace limit")
        for _, _, spec, origin in declarations(path):
            if "path" not in spec:
                continue
            target = local_path(origin, spec["path"], "Cargo.toml")
            if target not in manifests:
                gap("cargo_local_dependency_unverified", path)
                continue
            target_parent = PurePosixPath(target).parent
            if not target_parent.is_relative_to(base) or any(
                matches(target_parent.relative_to(base).as_posix(), p) for p in excludes
            ):
                gap("cargo_local_dependency_unverified", path)
                continue
            if target not in members:
                members.add(target)
                pending.append(target)

    local_nodes, visits = set(), 0
    for path in sorted(members):
        manifest = manifests[path]
        if manifest.get("replace") or manifest.get("patch"):
            gap("cargo_source_unverified", path)
        if path != rootpath and "workspace" in manifest:
            gap("cargo_manifest_unassigned", path)
        package = manifest.get("package")
        if package is None and path == rootpath and "workspace" in root:
            continue
        if not isinstance(package, dict) or not isinstance(package.get("name"), str):
            gap("cargo_manifest_invalid", path)
            continue
        if "workspace" in package and local_path(path, package["workspace"], "Cargo.toml") != rootpath:
            gap("cargo_manifest_unassigned", path)
        declared_version = package.get("version")
        if isinstance(declared_version, dict) and declared_version.get("workspace") is True:
            declared_version = workspace.get("package", {}).get("version")
        candidates = [k for k in by_name.get(package["name"], []) if not k[2] and k[1] == declared_version]
        project = {"path": path, "lockfile": lockfile, "system": "cargo", "direct_dependencies": []}
        projects.append(project)
        if len(candidates) != 1:
            gap("manifest_lock_mismatch", path)
            continue
        start = candidates[0]
        local_nodes.add(start)
        declared_names = set()
        for group, alias, spec, origin in declarations(path):
            name = spec.get("package", alias)
            if not isinstance(name, str) or not NAME.fullmatch(name):
                gap("invalid_manifest_dependency", path)
                continue
            declared_names.add(name)
            candidates = [k for k in edges[start] if k[0] == name]
            if "git" in spec or "registry" in spec or "path" in spec:
                # Never reinterpret a custom source as the public crate with the same name.
                if "path" not in spec:
                    gap("cargo_source_unverified", path)
                candidates = [k for k in candidates if not k[2]] if "path" in spec else []
            else:
                candidates = [k for k in candidates if k[2] in CRATES_IO]
            if not candidates:
                gap("manifest_lock_mismatch", path)
                continue
            outcomes = [(k, requirement_matches(spec.get("version", "*"), k[1])) for k in candidates]
            matched = [k for k, ok in outcomes if ok is True]
            if len(matched) != 1:
                gap(
                    "cargo_requirement_unverified"
                    if any(ok is None for _, ok in outcomes)
                    else "manifest_lock_mismatch",
                    path,
                )
                continue
            key = matched[0]
            if key not in packages:
                continue
            use = {"system": "cargo", "name": name, "version": key[1], "group": group, "declared_name": alias}
            project["direct_dependencies"].append(use)
            packages[key]["direct_uses"].append({"project": path, **use})
        if {k[0] for k in edges[start]} - declared_names:
            gap("stale_workspace_dependencies", path)
        pending, seen = deque([start]), set()
        while pending:
            key = pending.popleft()
            if key in seen:
                continue
            seen.add(key)
            visits += 1
            if visits > 100000:
                raise ValueError("Cargo graph traversal limit")
            if key in packages:
                packages[key]["projects"].append(path)
            pending.extend(edges[key])
    for key in nodes:
        if not key[2] and key not in local_nodes:
            gap("cargo_local_dependency_unverified")
    for package in packages.values():
        if not package["projects"]:
            gap("unattributed_lock_entry")
    return {
        "projects": projects,
        "packages": list(packages.values()),
        "coverage_gaps": gaps,
        "unresolved": unresolved,
        "used_manifests": sorted(members),
    }
