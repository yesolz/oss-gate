"""Static Go declaration screening. Requirements are never called a build list."""

import hashlib
import json
import posixpath
import re
from pathlib import PurePosixPath

from .yarn import VERSION

TOKEN = re.compile(r'//[^\n]*|"(?:\\.|[^"\\])*"|`[^`]*`|=>|[()]|[^\s()"`]+')
NAME = re.compile(r"[A-Za-z0-9._~+\-/]+\Z")


def module_name(value):
    return (
        isinstance(value, str)
        and len(value) <= 512
        and NAME.fullmatch(value)
        and not value.startswith("/")
        and all(p not in ("", ".", "..") for p in value.split("/"))
    )


def version(value):
    return isinstance(value, str) and value.startswith("v") and VERSION.fullmatch(value[1:])


def local_path(base, value, filename="go.mod"):
    """Resolve only an inventory key, never open or traverse the requested path."""
    if not isinstance(value, str) or not value or value.startswith("/") or "\\" in value or ":" in value:
        return None
    path = posixpath.normpath(posixpath.join(str(PurePosixPath(base).parent), value, filename))
    return None if path == ".." or path.startswith("../") else path


def parse(text, work=False):
    result, block = {}, None
    if len(text.splitlines()) > 20000:
        raise ValueError("Go directive limit")
    for line in text.splitlines():
        tokens, indirect, end = [], False, 0
        for match in TOKEN.finditer(line):
            if line[end : match.start()].strip():
                raise ValueError("invalid Go token")
            end = match.end()
            token = match.group()
            if token.startswith("//"):
                indirect = token[2:].strip() == "indirect"
                break
            if token.startswith('"'):
                token = json.loads(token)
            elif token.startswith("`"):
                token = token[1:-1]
            if not isinstance(token, str) or any(ord(c) < 32 for c in token):
                raise ValueError("invalid Go string")
            tokens.append(token)
        if line[end:].strip():
            raise ValueError("invalid Go token")
        if not tokens:
            continue
        if tokens == [")"] and block:
            block = None
            continue
        key = block or tokens.pop(0)
        if tokens == ["("] and not block:
            block = key
            continue
        if "(" in tokens or ")" in tokens or not tokens:
            raise ValueError("invalid Go block")
        result.setdefault(key, []).append((tokens, indirect))
    if block:
        raise ValueError("unclosed Go block")
    allowed = (
        {"go", "toolchain", "use", "replace", "godebug"}
        if work
        else {
            "module",
            "go",
            "toolchain",
            "require",
            "replace",
            "exclude",
            "retract",
            "tool",
            "godebug",
            "ignore",
        }
    )
    if result.keys() - allowed:
        raise ValueError("unknown Go directive")
    for key in ("module", "go", "toolchain"):
        if key in result and (len(result[key]) != 1 or len(result[key][0][0]) != 1):
            raise ValueError("invalid singleton directive")
    if not work and ("module" not in result or not module_name(result["module"][0][0][0])):
        raise ValueError("missing module identity")
    for key in ("require", "exclude"):
        seen = set()
        for parts, _ in result.get(key, []):
            identity = parts[0] if key == "require" else tuple(parts)
            if len(parts) != 2 or not module_name(parts[0]) or not version(parts[1]) or identity in seen:
                raise ValueError("invalid or duplicate Go requirement")
            seen.add(identity)
    for parts, _ in result.get("use", []):
        if len(parts) != 1:
            raise ValueError("invalid workspace use")
    replacements = {}
    for parts, _ in result.get("replace", []):
        if parts.count("=>") != 1:
            raise ValueError("invalid replacement")
        i = parts.index("=>")
        old, new = parts[:i], parts[i + 1 :]
        if (
            len(old) not in (1, 2)
            or len(new) not in (1, 2)
            or not module_name(old[0])
            or (len(old) == 2 and not version(old[1]))
            or (len(new) == 2 and (not module_name(new[0]) or not version(new[1])))
        ):
            raise ValueError("invalid replacement identity")
        key = tuple(old)
        if key in replacements:
            raise ValueError("duplicate replacement")
        replacements[key] = new
    result["replacements"] = replacements
    return result


def analyze(contents):
    """Return declared identities, preserving workspace and replacement uncertainty."""
    projects, packages, gaps, unresolved, statuses = [], [], [], [], {}
    modules, works = {}, {}

    def gap(code, source):
        gaps.append({"code": code, "source": source})

    for path, text in sorted(contents.items()):
        name = PurePosixPath(path).name
        if name in {"go.sum", "go.work.sum"}:
            statuses[path] = "checksum_only"
            continue
        if name not in {"go.mod", "go.work"}:
            continue
        try:
            value = parse(text, work=name == "go.work")
            (works if name == "go.work" else modules)[path] = value
            statuses[path] = "parsed_declarations"
        except (ValueError, TypeError, RecursionError):
            statuses[path] = "invalid_or_unsupported"
            gap("go_manifest_invalid", path)

    contexts = {}
    for path, work in works.items():
        members, incomplete = set(), False
        for parts, _ in work.get("use", []):
            target = local_path(path, parts[0])
            if target not in modules:
                gap("go_workspace_member_missing", path)
                incomplete = True
            else:
                members.add(target)
        replacements, conflicts = {}, set()
        for member in sorted(members):
            for key, value in modules[member]["replacements"].items():
                if key in replacements and replacements[key] != value:
                    conflicts.add(key[0])
                replacements[key] = value
        replacements.update(work["replacements"])
        for key in work["replacements"]:
            # A wildcard work replacement overrides all module-specific versions.
            if len(key) == 1:
                conflicts.discard(key[0])
                replacements = {k: v for k, v in replacements.items() if k[0] != key[0] or len(k) == 1}
        local_names = {modules[m]["module"][0][0][0] for m in members}
        if len(local_names) != len(members):
            gap("go_workspace_conflict", path)
        for member in members:
            contexts.setdefault(member, []).append((path, replacements, conflicts, local_names, incomplete))

    for path, mod in modules.items():
        project = {"path": path, "lockfile": None, "system": "go", "direct_dependencies": []}
        projects.append(project)
        gap("go_build_list_unverified", path)
        context = contexts.get(path, [])
        if len(context) > 1:
            gap("go_workspace_conflict", path)
            continue
        if context and context[0][4]:
            gap("go_workspace_conflict", path)
            continue
        # An unreadable workspace may replace any module. Never assume the originals.
        ancestors = {str(p / "go.work") for p in PurePosixPath(path).parents}
        if any(p in ancestors and s == "invalid_or_unsupported" for p, s in statuses.items()):
            gap("go_workspace_conflict", path)
            continue
        replacements = context[0][1] if context else mod["replacements"]
        conflicts = context[0][2] if context else set()
        local_names = context[0][3] if context else {mod["module"][0][0][0]}
        excluded = {tuple(parts) for parts, _ in mod.get("exclude", [])}
        if context:
            workpath = context[0][0]
            for parts, _ in works[workpath].get("use", []):
                member = modules.get(local_path(workpath, parts[0]), {})
                excluded.update(tuple(p) for p, _ in member.get("exclude", []))
        for (name, declared_version), indirect in mod.get("require", []):
            if name in local_names:
                continue
            if name in conflicts or (name, declared_version) in excluded:
                gap("go_requirement_unresolved", path)
                continue
            replacement = replacements.get((name, declared_version), replacements.get((name,)))
            if replacement and len(replacement) == 1:
                gap("go_local_replacement", path)
                unresolved.append(
                    {
                        "source": path,
                        "dependency": name,
                        "source_type": "local",
                        "locator_sha256": hashlib.sha256(replacement[0].encode()).hexdigest(),
                    }
                )
                continue
            actual_name, actual_version = replacement or (name, declared_version)
            identity = {"system": "go", "name": actual_name, "version": actual_version}
            use = {**identity, "group": "indirect" if indirect else "require", "declared_name": name}
            if not indirect:
                project["direct_dependencies"].append(use)
            packages.append(
                {
                    **identity,
                    "lockfile": path,
                    "projects": [path],
                    "direct_uses": [] if indirect else [{"project": path, **use}],
                    "basis": "declared_requirement",
                }
            )
    return {
        "projects": projects,
        "packages": packages,
        "coverage_gaps": gaps,
        "unresolved": unresolved,
        "statuses": statuses,
    }
