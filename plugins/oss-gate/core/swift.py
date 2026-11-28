"""Swift Package.resolved pins. No evaluation of executable Package.swift files."""

from pathlib import PurePosixPath as Path
import re
from urllib.parse import urlsplit, urlunsplit

from .repo_inputs import empty, gap, object_json, package, unresolved
from .yarn import VERSION


def repository_url(value):
    if not isinstance(value, str) or len(value) > 2048 or re.search(r"[\x00-\x20\x7f%\\]", value):
        return None
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.port not in (None, 443)
            or parsed.query
            or parsed.fragment
        ):
            return None
        path = parsed.path.rstrip("/").removesuffix(".git")
        if not path or any(p in {"", ".", ".."} for p in path.lstrip("/").split("/")):
            return None
        if not re.fullmatch(r"/[A-Za-z0-9_./~-]+", path):
            return None
        if parsed.hostname == "github.com":
            if len(path.strip("/").split("/")) != 2:
                return None
            path = path.lower()
        return urlunsplit(("https", parsed.hostname.lower(), path, "", ""))
    except ValueError:
        return None


def parse(text, source, project):
    result = empty()
    data = object_json(text)
    schema = data.get("version")
    if type(schema) is not int or schema not in (1, 2, 3):
        raise ValueError("unsupported Swift lock schema")
    body = data.get("object") if schema == 1 else data
    if not isinstance(body, dict) or not isinstance(body.get("pins"), list) or len(body["pins"]) > 10000:
        raise ValueError("invalid Swift pins")
    seen = set()
    for pin in body["pins"]:
        if not isinstance(pin, dict) or not isinstance(pin.get("state"), dict):
            raise ValueError("invalid Swift state")
        location = pin.get("repositoryURL") if schema == 1 else pin.get("location")
        identity = pin.get("package") if schema == 1 else pin.get("identity")
        if not isinstance(identity, str) or not identity or len(identity) > 256 or identity.lower() in seen:
            raise ValueError("invalid/duplicate Swift identity")
        seen.add(identity.lower())
        kind = "remoteSourceControl" if schema == 1 else pin.get("kind")
        name = repository_url(location)
        state = pin["state"]
        version, revision = state.get("version"), state.get("revision")
        if kind != "remoteSourceControl" or name is None:
            gap(result, "swift_source_unverified", source)
            unresolved(result, source, "swift_source", location)
            continue
        if not isinstance(version, str) or not VERSION.fullmatch(version) or state.get("branch"):
            gap(result, "swift_nonversion_pin", source)
            unresolved(result, source, "swift_nonversion_pin", location + str(state))
            continue
        if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", revision):
            gap(result, "swift_revision_unverified", source)
            revision = None
        # OSV SwiftURL uses host/path, without the transport scheme or .git suffix.
        result["packages"].append(
            package("swift", name.removeprefix("https://"), version, source, project, revision=revision)
        )
    result["projects"].append({"path": project, "lockfile": source, "system": "swift", "direct_dependencies": []})
    gap(result, "swift_manifest_resolution_unverified", source)
    gap(result, "swift_advisory_aliases_unverified", source)
    return result


def analyze(contents):
    result, assigned = empty(), set()
    for source, text in sorted(contents.items()):
        if Path(source).name != "Package.resolved":
            result["statuses"][source] = "configuration_not_executed"
            continue
        # Xcode pin files may live inside .xcodeproj/.xcworkspace directories.
        project = next(
            (
                str(parent / "Package.swift")
                for parent in Path(source).parents
                if str(parent / "Package.swift") in contents
            ),
            source,
        )
        try:
            parsed = parse(text, source, project)
            for key in ("projects", "packages", "coverage_gaps", "unresolved"):
                result[key].extend(parsed[key])
            result["statuses"][source] = "parsed"
            assigned.add(project)
        except (ValueError, TypeError, RecursionError):
            result["statuses"][source] = "invalid_or_unsupported"
            gap(result, "swift_resolution_invalid", source)
    for source in contents.keys() - assigned:
        if Path(source).name == "Package.swift":
            result["projects"].append({"path": source, "lockfile": None, "system": "swift", "direct_dependencies": []})
            gap(result, "swift_resolved_input_missing", source)
    return result
