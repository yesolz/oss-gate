"""Offline Docker references and bounded Trivy/Grype image report imports."""

import math
from pathlib import PurePosixPath as Path
import re

import yaml

from .licenses import classify_license
from .policy import RANK
from .repo_inputs import empty, gap, object_json, unresolved
from .yarn import LockLoader

DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
TOKEN = re.compile(r"[A-Za-z0-9_.:+~/-]{1,512}\Z")
ADVISORY = re.compile(r"[A-Za-z0-9_.:-]{1,256}\Z")
MAX_ITEMS = 20000


def image_reference(value):
    if not isinstance(value, str) or len(value) > 1024 or not re.fullmatch(r"[A-Za-z0-9._:/@-]+", value):
        return None
    if "://" in value or value.count("@") > 1:
        return None
    name, sep, digest = value.partition("@")
    if sep and not DIGEST.fullmatch(digest):
        return None
    parts = name.split("/")
    if any(p in {"", ".", ".."} for p in parts):
        return None
    final = parts[-1].split(":")
    if len(final) > 2 or not re.fullmatch(r"[a-z0-9]+(?:(?:[._-]+)[a-z0-9]+)*", final[0]):
        return None
    if len(final) == 2 and not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", final[1]):
        return None
    parts[-1] = final[0]
    if len(parts) == 1 or not ("." in parts[0] or ":" in parts[0] or parts[0] == "localhost"):
        parts.insert(0, "docker.io")
    if parts[0] in {"index.docker.io", "registry-1.docker.io"}:
        parts[0] = "docker.io"
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?(?::[0-9]{1,5})?", parts[0]):
        return None
    if parts[0] == "docker.io" and len(parts) == 2:
        parts.insert(1, "library")
    if any(not re.fullmatch(r"[a-z0-9]+(?:[._-]+[a-z0-9]+)*", p) for p in parts[1:]):
        return None
    # Digest defines identity; a redundant tag does not change it.
    return "/".join(parts) + ("@" + digest if sep else ":" + (final[1] if len(final) == 2 else "latest"))


def sequence(value, nullable=False):
    if value is None and nullable:
        return []
    if not isinstance(value, list) or len(value) > MAX_ITEMS:
        raise ValueError("invalid or oversized report list")
    return value


def token(value):
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise ValueError("invalid package identity")
    return value


def score(values):
    valid = [v for v in values if type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 10]
    return max(valid) if valid else None


def finding(identifier, name, version, namespace, severity, scores, fixed, suppressed=False):
    if not isinstance(identifier, str) or not ADVISORY.fullmatch(identifier):
        raise ValueError("invalid advisory identity")
    severity = severity.upper() if isinstance(severity, str) else "UNKNOWN"
    if severity not in {"CRITICAL", "HIGH", "MEDIUM", "LOW", "NEGLIGIBLE", "UNKNOWN"}:
        severity = "UNKNOWN"
    number = score(scores)
    outcome = "hold" if severity in {"HIGH", "CRITICAL"} or (number is not None and number >= 7) else "conditional"
    return {
        "id": identifier,
        "name": token(name),
        "version": token(version),
        "namespace": namespace,
        "severity": severity,
        "score": number,
        "fixed_versions": [token(v) for v in fixed],
        "suppressed": suppressed,
        "outcome": outcome,
    }


def licenses(value):
    if value is None:
        return None
    if not isinstance(value, list) or len(value) > 100 or any(not isinstance(v, str) or len(v) > 512 for v in value):
        raise ValueError("invalid license metadata")
    return value


def trivy(data):
    if (
        data.get("SchemaVersion") != 2
        or type(data.get("SchemaVersion")) is not int
        or data.get("ArtifactType") != "container_image"
    ):
        raise ValueError("expected Trivy v2 container image report")
    metadata = data.get("Metadata")
    if not isinstance(metadata, dict) or "Results" not in data:
        raise ValueError("missing Trivy image/results metadata")
    refs = sequence(metadata.get("RepoDigests", []))
    scan = {
        "scanner": "trivy",
        "scanner_version": None,
        "created_at": data.get("CreatedAt"),
        "references": refs,
        "image_id": metadata.get("ImageID"),
        "packages": [],
        "findings": [],
        "inventory_complete": False,
        "ignored_count": 0,
    }
    if isinstance(data.get("Trivy"), dict):
        scan["scanner_version"] = data["Trivy"].get("Version")
    results = sequence(data["Results"])
    for section in results:
        if not isinstance(section, dict):
            raise ValueError("invalid Trivy result")
        if section.get("Class") not in {"os-pkgs", "lang-pkgs"}:
            continue
        namespace = token(section.get("Type", "unknown"))
        # A list may be filtered; presence is not proof of complete inventory.
        for item in sequence(section.get("Packages", []), nullable=True):
            if not isinstance(item, dict):
                raise ValueError("invalid Trivy package")
            scan["packages"].append(
                {
                    "name": token(item.get("Name")),
                    "version": token(item.get("Version")),
                    "namespace": namespace,
                    "licenses": licenses(item.get("Licenses")),
                }
            )
        for suppressed, items in (
            (False, section.get("Vulnerabilities", [])),
            (True, section.get("ModifiedFindings", [])),
        ):
            for item in sequence(items, nullable=True):
                if not isinstance(item, dict):
                    raise ValueError("invalid Trivy vulnerability")
                if suppressed:
                    item = item.get("Finding", item)
                    scan["ignored_count"] += 1
                    if not isinstance(item, dict) or "VulnerabilityID" not in item:
                        continue
                cvss = item.get("CVSS", {}) or {}
                if not isinstance(cvss, dict):
                    raise ValueError("invalid CVSS metadata")
                scores = [
                    v
                    for entry in cvss.values()
                    if isinstance(entry, dict)
                    for k, v in entry.items()
                    if k in {"V2Score", "V3Score", "V4Score"}
                ]
                fixed = item.get("FixedVersion", "")
                if not isinstance(fixed, str):
                    raise ValueError("invalid fixed version")
                scan["findings"].append(
                    finding(
                        item.get("VulnerabilityID"),
                        item.get("PkgName"),
                        item.get("InstalledVersion"),
                        namespace,
                        item.get("Severity"),
                        scores,
                        [s.strip() for s in fixed.split(",") if s.strip()],
                        suppressed,
                    )
                )
    return scan


def grype(data):
    descriptor, source = data.get("descriptor"), data.get("source")
    if (
        not isinstance(descriptor, dict)
        or descriptor.get("name") != "grype"
        or not isinstance(source, dict)
        or source.get("type") != "image"
        or not isinstance(source.get("target"), dict)
    ):
        raise ValueError("expected Grype image report")
    target = source["target"]
    scan = {
        "scanner": "grype",
        "scanner_version": None if descriptor.get("version") in ("", "[not provided]") else descriptor.get("version"),
        "created_at": descriptor.get("timestamp") or None,
        "references": sequence(target.get("repoDigests", [])),
        "image_id": target.get("imageID"),
        "manifest_digest": target.get("manifestDigest"),
        "packages": [],
        "findings": [],
        "inventory_complete": False,
        "ignored_count": 0,
    }
    for suppressed, items in ((False, data.get("matches")), (True, data.get("ignoredMatches", []))):
        for item in sequence(items):
            if not isinstance(item, dict):
                raise ValueError("invalid Grype match")
            vuln, artifact = item.get("vulnerability"), item.get("artifact")
            if not isinstance(vuln, dict) or not isinstance(artifact, dict):
                raise ValueError("missing Grype vulnerability/artifact")
            fix = vuln.get("fix", {})
            if not isinstance(fix, dict):
                raise ValueError("invalid Grype fix")
            namespace = token(vuln.get("namespace", artifact.get("type", "unknown")))
            scores = [
                entry.get("metrics", {}).get("baseScore")
                for entry in sequence(vuln.get("cvss", []))
                if isinstance(entry, dict) and isinstance(entry.get("metrics"), dict)
            ]
            scan["findings"].append(
                finding(
                    vuln.get("id"),
                    artifact.get("name"),
                    artifact.get("version"),
                    namespace,
                    vuln.get("severity"),
                    scores,
                    sequence(fix.get("versions", []), nullable=True),
                    suppressed,
                )
            )
            scan["packages"].append(
                {
                    "name": token(artifact.get("name")),
                    "version": token(artifact.get("version")),
                    "namespace": namespace,
                    "licenses": licenses(artifact.get("licenses")),
                }
            )
            scan["ignored_count"] += int(suppressed)
    return scan


def normalize_scan(scan, source):
    if len(scan["packages"]) > MAX_ITEMS or len(scan["findings"]) > MAX_ITEMS:
        raise ValueError("container import limit")
    refs = [image_reference(v) for v in scan["references"]]
    if any(r is None or "@sha256:" not in r for r in refs):
        raise ValueError("invalid image digest reference")
    scan["references"] = sorted(set(refs))
    scan["source"] = source
    for key in ("image_id", "manifest_digest"):
        if scan.get(key) is not None and (not isinstance(scan[key], str) or not DIGEST.fullmatch(scan[key])):
            raise ValueError("invalid image digest")
    if scan["scanner_version"] is not None:
        scan["scanner_version"] = token(scan["scanner_version"])
    timestamp = scan["created_at"]
    if timestamp is not None:
        from .additional_policy import timestamp as parse_time

        if not isinstance(timestamp, str) or not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,9})?(?:Z|[+-][0-9]{2}:[0-9]{2})",
            timestamp,
        ):
            raise ValueError("invalid scanner timestamp")
        # Go scanners emit RFC3339Nano; Python 3.10 accepts only 3/6 fractional digits.
        # Validate a microsecond copy and preserve the original recorded precision.
        compatible = re.sub(r"\.([0-9]+)", lambda m: "." + m[1][:6].ljust(6, "0"), timestamp)
        parse_time(compatible)
    # Keep per-package, per-namespace findings; do not deduplicate different distro matches by CVE alone.
    unique = {}
    for item in scan["findings"]:
        key = tuple(item[k] for k in ("namespace", "name", "version", "id", "suppressed"))
        if key not in unique or RANK[item["outcome"]] > RANK[unique[key]["outcome"]]:
            unique[key] = item
    scan["findings"] = list(unique.values())
    # Preserve license uncertainty when duplicate records disagree.
    packages = {}
    for item in scan["packages"]:
        key = tuple(item[k] for k in ("namespace", "name", "version"))
        if key in packages and packages[key]["licenses"] != item["licenses"]:
            packages[key]["licenses"] = None
        else:
            packages.setdefault(key, item)
    scan["packages"] = list(packages.values())
    for item in scan["packages"]:
        item["license_assessment"] = classify_license(item["licenses"])
    scan["overall"] = max(
        [
            "conditional",
            *(f["outcome"] for f in scan["findings"]),
            *(p["license_assessment"]["tier"] for p in scan["packages"]),
        ],
        key=RANK.get,
    )
    return scan


def analyze(contents):
    result = empty()
    result.update(container_scans=[], container_images=[])

    def reference(source, value, role):
        canonical = image_reference(value)
        if canonical is None:
            gap(result, "container_reference_unresolved", source)
            unresolved(result, source, "container_reference", value)
            return
        result["container_images"].append({"source": source, "reference": canonical, "role": role})

    for source, text in sorted(contents.items()):
        name = Path(source).name
        try:
            if name in {"trivy.json", "grype.json"} or name.endswith((".trivy.json", ".grype.json")):
                data = object_json(text)
                scan = normalize_scan(trivy(data) if name.endswith("trivy.json") else grype(data), source)
                result["container_scans"].append(scan)
                gap(result, "container_scan_coverage_unverified", source)
                if not scan["references"]:
                    gap(result, "container_digest_unverified", source)
                if scan["ignored_count"]:
                    gap(result, "container_suppressed_findings", source)
                if not scan["packages"] or any(not p["licenses"] for p in scan["packages"]):
                    gap(result, "container_licenses_unverified", source)
                project = {"path": source, "lockfile": source, "system": "container", "direct_dependencies": []}
            elif name in {"compose.yml", "compose.yaml", "docker-compose.yml", "docker-compose.yaml"}:
                data = yaml.load(text, Loader=LockLoader)
                if not isinstance(data, dict) or not isinstance(data.get("services"), dict):
                    raise ValueError("invalid Compose services")
                for service in data["services"].values():
                    if not isinstance(service, dict):
                        raise ValueError("invalid Compose service")
                    if "image" in service:
                        reference(source, service["image"], "compose")
                    if "build" in service or "image" not in service:
                        gap(result, "container_final_image_unverified", source)
                if any(k in data for k in ("include", "extends")) or any(
                    "extends" in s for s in data["services"].values()
                ):
                    gap(result, "container_reference_unresolved", source)
                project = {"path": source, "lockfile": None, "system": "container", "direct_dependencies": []}
            else:
                stages, count = set(), 0
                if re.search(r"(?im)^\s*#\s*(escape|syntax)\s*=", text):
                    gap(result, "container_reference_unresolved", source)
                for line in re.sub(r"\\\r?\n", " ", text).splitlines():
                    if not re.match(r"\s*FROM\s", line, re.I):
                        continue
                    fields = line.split()[1:]
                    if fields and fields[0].startswith("--platform="):
                        fields.pop(0)
                    if len(fields) not in {1, 3} or (len(fields) == 3 and fields[1].lower() != "as"):
                        raise ValueError("unresolved Docker FROM")
                    base = fields[0]
                    if base.lower() not in stages and base.lower() != "scratch":
                        reference(source, base, "base")
                    if len(fields) == 3:
                        stages.add(fields[2].lower())
                    stages.add(str(count))
                    count += 1
                if not count:
                    raise ValueError("missing Docker FROM")
                gap(result, "container_final_image_unverified", source)
                project = {"path": source, "lockfile": None, "system": "container", "direct_dependencies": []}
            result["projects"].append(project)
            result["statuses"][source] = "parsed"
        except (ValueError, TypeError, KeyError, RecursionError, yaml.YAMLError):
            result["statuses"][source] = "invalid_or_unsupported"
            gap(result, "container_input_invalid", source)
    scanned = {r for scan in result["container_scans"] for r in scan["references"]}
    for image in result["container_images"]:
        image["matched_reports"] = [
            s["source"] for s in result["container_scans"] if image["reference"] in s["references"]
        ]
        if image["reference"] not in scanned:
            gap(result, "container_scan_missing", image["source"])
    return result
