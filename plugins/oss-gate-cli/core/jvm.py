"""Maven resolved JSON trees and Gradle dependency locks for Java and Kotlin."""

from pathlib import PurePosixPath as Path
import re
import xml.etree.ElementTree as ET

from .repo_inputs import empty, gap, object_json, package

PART = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,255}\Z")
VERSION = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.+-]{0,255}\Z")
SCRIPTS = {"build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"}


def identity(group, artifact, version, allow_mutable=False):
    if not all(isinstance(x, str) for x in (group, artifact, version)):
        return None
    if (
        not PART.fullmatch(group)
        or not PART.fullmatch(artifact)
        or not VERSION.fullmatch(version)
        or "+" in version
        or version.upper() in {"LATEST", "RELEASE"}
        or (not allow_mutable and "SNAPSHOT" in version.upper())
    ):
        return None
    return {"system": "maven", "name": group + ":" + artifact, "version": version}


def pom_identity(text):
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)", text, re.I):
        raise ValueError("XML declarations not supported")
    root = ET.fromstring(text)
    if root.tag not in {"project", "{http://maven.apache.org/POM/4.0.0}project"}:
        raise ValueError("not a Maven POM")
    ns = "{http://maven.apache.org/POM/4.0.0}" if root.tag.startswith("{") else ""

    def value(name):
        node = root.find(ns + name)
        return (node.text or "").strip() if node is not None else ""

    return identity(value("groupId"), value("artifactId"), value("version"), allow_mutable=True)


def maven_tree(text, source, project):
    data = object_json(text)
    root_id = identity(data.get("groupId"), data.get("artifactId"), data.get("version"), allow_mutable=True)
    if not root_id:
        raise ValueError("invalid Maven tree root")
    rows, direct, gaps, edges = [], [], [], []
    pending = [(data, 0, None)]
    count = 0
    while pending:
        node, depth, parent = pending.pop()
        count += 1
        if count > 10000 or not isinstance(node, dict):
            raise ValueError("invalid/oversized Maven tree")
        included = node.get("included", "true")
        if included not in ("true", "false"):
            raise ValueError("invalid Maven verbose inclusion")
        if included == "false":
            if not depth:
                raise ValueError("omitted Maven root")
            gaps.append({"code": "jvm_omitted_nodes", "source": source})
            continue
        if "omittedReason" in node:
            raise ValueError("conflicting Maven inclusion")
        target = identity(node.get("groupId"), node.get("artifactId"), node.get("version"), allow_mutable=depth == 0)
        children = node.get("children", [])
        if not isinstance(children, list):
            raise ValueError("invalid Maven children")
        if depth:
            if not target:
                gaps.append({"code": "jvm_version_unresolved", "source": source})
            else:
                scope, classifier, artifact_type = (
                    node.get("scope", ""),
                    node.get("classifier", ""),
                    node.get("type", "jar"),
                )
                if not all(isinstance(v, str) and len(v) <= 128 for v in (scope, classifier, artifact_type)):
                    raise ValueError("invalid Maven artifact metadata")
                row = package(
                    **target,
                    source=source,
                    project=project,
                    basis="resolved_tree",
                    classifier=classifier,
                    artifact_type=artifact_type,
                    configuration=scope,
                )
                if classifier or artifact_type not in {"jar", "pom"}:
                    gaps.append({"code": "jvm_variant_unverified", "source": source})
                if scope == "system":
                    gaps.append({"code": "jvm_local_artifact", "source": source})
                else:
                    if depth == 1:
                        use = {**target, "group": scope or "compile", "declared_name": target["name"]}
                        direct.append(use)
                        row["direct_uses"].append({"project": project, **use})
                    rows.append(row)
                if parent:
                    edges.append({"from": parent, "to": target})
        pending.extend((child, depth + 1, target) for child in reversed(children))
    return root_id, rows, direct, gaps, edges


def gradle_lock(text, source, project, legacy=False):
    rows, configs, coordinates = [], set(), set()
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if len(lines) > 10000:
        raise ValueError("Gradle lock limit")
    empty_seen = False
    for line in lines:
        if legacy:
            coord, names = line, [Path(source).stem]
        else:
            coord, sep, values = line.partition("=")
            if not sep:
                raise ValueError("missing Gradle configurations")
            names = [v.strip() for v in values.split(",") if v.strip()]
        if any(not re.fullmatch(r"[A-Za-z0-9_:.$-]{1,256}", n) for n in names):
            raise ValueError("invalid Gradle configuration")
        if coord == "empty" and not legacy:
            if empty_seen:
                raise ValueError("duplicate empty configuration")
            empty_seen = True
            empty_configs = set(names)
            continue
        parts = coord.split(":")
        if len(parts) != 3 or coord in coordinates or not names:
            raise ValueError("invalid or duplicate Gradle coordinate")
        target = identity(*parts)
        if not target:
            raise ValueError("non-fixed Gradle identity")
        coordinates.add(coord)
        configs.update(names)
        rows.append(package(**target, source=source, project=project, configurations=names))
    if not legacy and (not empty_seen or configs & empty_configs):
        raise ValueError("missing or conflicting empty configuration")
    return rows


def analyze(contents):
    result, assigned = empty(), set()
    manifests = {p for p in contents if Path(p).name in SCRIPTS | {"pom.xml"}}
    for source, text in sorted(contents.items()):
        filename = Path(source).name
        if filename in SCRIPTS | {"pom.xml"}:
            result["statuses"][source] = "configuration_not_executed"
            continue
        try:
            if filename == "dependency-tree.json":
                project = str(Path(source).with_name("pom.xml"))
                root_id, rows, direct, gaps, edges = maven_tree(text, source, project)
                result["coverage_gaps"].extend(gaps)
                if project in contents:
                    try:
                        if pom_identity(contents[project]) != root_id:
                            gap(result, "jvm_manifest_identity_unverified", project)
                    except (ValueError, ET.ParseError):
                        gap(result, "jvm_manifest_identity_unverified", project)
                else:
                    gap(result, "jvm_manifest_missing", source)
                basis = "resolved_tree"
            elif filename.endswith(".lockfile"):
                legacy = "/gradle/dependency-locks/" in "/" + source
                parent = Path(source).parents[2] if legacy else Path(source).parent
                candidates = [
                    str(parent / name)
                    for name in ("build.gradle.kts", "build.gradle")
                    if str(parent / name) in contents
                ]
                project = candidates[0] if len(candidates) == 1 else str(parent / "build.gradle")
                if len(candidates) != 1:
                    gap(result, "jvm_manifest_missing", source)
                rows = gradle_lock(text, source, project, legacy)
                direct, edges, basis = [], [], "locked"
                gap(result, "jvm_dependency_edges_unverified", source)
            else:
                continue
            assigned.add(project)
            result["projects"].append(
                {
                    "path": project,
                    "lockfile": source,
                    "system": "maven",
                    "basis": basis,
                    "direct_dependencies": direct,
                    "dependency_edges": edges,
                }
            )
            result["packages"].extend(rows)
            result["statuses"][source] = "parsed"
            gap(result, "jvm_build_configuration_unverified", source)
        except (ValueError, TypeError, RecursionError):
            result["statuses"][source] = "invalid_or_unsupported"
            gap(result, "jvm_resolution_invalid", source)
    for project in sorted(manifests - assigned):
        if Path(project).name.startswith("settings."):
            gap(result, "jvm_build_configuration_unverified", project)
            continue
        result["projects"].append({"path": project, "lockfile": None, "system": "maven", "direct_dependencies": []})
        gap(result, "jvm_resolved_input_missing", project)
    grouped = {}
    for project in result["projects"]:
        existing = grouped.setdefault(project["path"], {**project, "lockfiles": []})
        if project["lockfile"] and project["lockfile"] not in existing["lockfiles"]:
            existing["lockfiles"].append(project["lockfile"])
        if existing is not project:
            for field in ("direct_dependencies", "dependency_edges"):
                for entry in project.get(field, []):
                    if entry not in existing.setdefault(field, []):
                        existing[field].append(entry)
    result["projects"] = list(grouped.values())
    return result
