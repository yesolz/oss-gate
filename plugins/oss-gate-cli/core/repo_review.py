"""Repository discovery and scoped dependency screening with immutable evidence."""

from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat

import httpx

from . import api, yarn, gomod, cargo
from .additional_policy import apply as apply_additional
from .license_policy import apply_license_policy
from .licenses import classify_license, DATA_SHA256
from .policy import advisory_groups, RANK
from .settings import CURRENT, EVENTS, PolicyBlocked, check, fingerprint, identifier
from .snapshot import new_run, seal, write_json
from .tls import EVIDENCE as TLS_EVIDENCE

SCHEMA = "oss-gate.repository-review/1"
POLICY = "oss-gate.repository-policy/1"
EXCLUDED = {".git", "node_modules", ".yarn", ".venv", "venv", "target", "build", "dist", ".gradle", ".build", "Pods"}
FORMATS = {
    "package.json": "npm",
    "yarn.lock": "yarn",
    "package-lock.json": "npm-lock",
    "pnpm-lock.yaml": "pnpm",
    "bun.lock": "bun",
    "bun.lockb": "bun",
    "go.mod": "go",
    "go.sum": "go",
    "go.work": "go",
    "go.work.sum": "go",
    "Cargo.toml": "cargo",
    "Cargo.lock": "cargo",
    "pom.xml": "maven",
    "build.gradle": "gradle",
    "build.gradle.kts": "gradle",
    "settings.gradle": "gradle",
    "settings.gradle.kts": "gradle",
    "gradle.lockfile": "gradle",
    "buildscript-gradle.lockfile": "gradle",
    "Package.swift": "swift",
    "Package.resolved": "swift",
    "Dockerfile": "docker",
    "compose.yml": "docker",
    "compose.yaml": "docker",
    "docker-compose.yml": "docker",
    "docker-compose.yaml": "docker",
    "requirements.txt": "python",
    "pyproject.toml": "python",
    "uv.lock": "python",
    "poetry.lock": "python",
    "Pipfile.lock": "python",
}
MAX_FILE_BYTES = 8_000_000
MAX_TOTAL_BYTES = 32_000_000
MAX_FILES = 2000
MAX_WALK_ENTRIES = 50000
MAX_ADVISORIES = 1000


def _json(text):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    value = json.loads(text, object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError("manifest must be an object")
    return value


def discover(root, output_root=None):
    root = Path(root).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("repository must be a local directory")
    output = Path(output_root).expanduser().resolve() if output_root else None
    if output == root:
        raise ValueError("output directory must differ from the repository root")
    files, contents, gaps, exclusions = [], {}, [], []
    count = total = 0

    def gap(code, source="."):
        gaps.append({"code": code, "source": source})

    def walk_error(error):
        gap("directory_unreadable")

    for directory, dirs, names in os.walk(root, followlinks=False, onerror=walk_error):
        directory = Path(directory)
        count += len(dirs) + len(names)
        if count > MAX_WALK_ENTRIES:
            gap("discovery_limit")
            break
        for name in sorted(dirs[:]):
            path = directory / name
            relative = path.relative_to(root).as_posix()
            if name in EXCLUDED or path == output:
                dirs.remove(name)
                exclusions.append({"path": relative, "reason": "generated_or_output_directory"})
            elif path.is_symlink():
                dirs.remove(name)
                gap("symlink_skipped", relative)
        dirs.sort()
        for name in sorted(names):
            kind = FORMATS.get(name)
            if name in {"config", "config.toml"} and directory.name == ".cargo":
                kind = "cargo-config"
            if name.startswith("Dockerfile.") or name.endswith(".Dockerfile"):
                kind = "docker"
            if kind is None:
                continue
            path = directory / name
            relative = path.relative_to(root).as_posix()
            if len(files) >= MAX_FILES:
                gap("discovery_limit")
                dirs[:] = []
                break
            row = {"path": relative, "format": kind, "status": "detected"}
            files.append(row)
            try:
                if path.is_symlink() or not path.resolve().is_relative_to(root):
                    raise ValueError("symlink")
                fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
                with os.fdopen(fd, "rb") as source:
                    if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                        raise ValueError("not a regular file")
                    remaining = MAX_TOTAL_BYTES - total
                    if remaining <= 0:
                        raise ValueError("total byte limit")
                    data = source.read(min(MAX_FILE_BYTES, remaining) + 1)
                total += len(data)
                if len(data) > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                    raise ValueError("file limit")
                row.update(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
                if kind in ("npm", "yarn", "go", "cargo"):
                    contents[relative] = data.decode("utf-8")
                else:
                    row["status"] = "unsupported"
                    gap("unsupported_format", relative)
            except (OSError, ValueError):
                row["status"] = "unreadable"
                gap("file_unreadable_or_limited", relative)
        if len(files) >= MAX_FILES or total > MAX_TOTAL_BYTES:
            gap("discovery_limit")
            break

    manifests = {}
    for file in files:
        if file["format"] != "npm" or file["path"] not in contents:
            continue
        try:
            manifests[file["path"]] = _json(contents[file["path"]])
        except (ValueError, RecursionError):
            file["status"] = "invalid"
            gap("invalid_manifest", file["path"])
    locks = {file["path"]: file for file in files if file["format"] == "yarn"}
    assignments = {lock: {} for lock in locks}
    for path, manifest in manifests.items():
        parent = Path(path).parent
        nearest = next((str(p / "yarn.lock") for p in (parent, *parent.parents) if str(p / "yarn.lock") in locks), None)
        if nearest is None:
            gap("lockfile_missing", path)
        else:
            assignments[nearest][parent.relative_to(Path(nearest).parent).as_posix()] = manifest
    projects, packages, unresolved = [], {}, []

    def merge(result):
        projects.extend(result["projects"])
        gaps.extend(result["coverage_gaps"])
        unresolved.extend(result["unresolved"])
        for package in result["packages"]:
            key = (package["system"], package["name"], package["version"])
            item = packages.setdefault(key, {k: package[k] for k in ("system", "name", "version")})
            occurrence = {k: package[k] for k in ("lockfile", "projects", "direct_uses")}
            occurrence["basis"] = package.get("basis", "locked")
            item.setdefault("occurrences", []).append(occurrence)

    for path, file in sorted(locks.items()):
        if path not in contents:
            continue
        try:
            result = yarn.analyze(contents[path], assignments[path], path)
            file["status"] = "parsed"
            merge(result)
        except (ValueError, TypeError, RecursionError):
            file["status"] = "invalid_or_unsupported"
            gap("lockfile_invalid_or_unsupported", path)
    for kind, adapter in (("go", gomod), ("cargo", cargo)):
        inputs = {f["path"]: contents.get(f["path"], "__unreadable__") for f in files if f["format"] == kind}
        result = adapter.analyze(inputs)
        merge(result)
        for file in files:
            if file["path"] in result["statuses"] and file["status"] == "detected":
                file["status"] = result["statuses"][file["path"]]
    if not projects:
        gap("no_supported_projects")
    # Project manifests are parsed only when their lock and workspace are recognized.
    used = {p["path"] for p in projects}
    for file in files:
        if file["format"] == "npm" and file["status"] == "detected":
            file["status"] = "parsed" if file["path"] in used else "unresolved"
    return {
        "schema": "oss-gate.repository-inventory/1",
        "root": str(root),
        "name": root.name,
        "files": files,
        "projects": projects,
        "packages": [packages[key] for key in sorted(packages)],
        "coverage_gaps": gaps,
        "exclusions": exclusions,
        "network_performed": False,
        "unresolved_dependencies": unresolved,
        "scope": "Yarn Berry npm and Cargo crates.io lock inventories, plus Go declared requirements. Includes development, optional and target-specific entries. Go build selection, installed/deployed artifacts, custom sources and external package-manager configuration remain unverified.",
    }


def plan_repository(root, output_root=None):
    return discover(root, output_root)


def _osv(packages):
    """Batch exact versions and follow each query's pagination with explicit bounds."""
    output = [{"ids": None, "complete": False} for _ in packages]
    page_budget = 200

    def unpack(result):
        if not isinstance(result, dict) or result.get("error"):
            raise ValueError("invalid OSV result")
        vulns = result.get("vulns", [])
        token = result.get("next_page_token")
        if not isinstance(vulns, list) or any(
            not isinstance(v, dict) or not isinstance(v.get("id"), str) or not v["id"] for v in vulns
        ):
            raise ValueError("invalid OSV advisories")
        if token is not None and (not isinstance(token, str) or len(token) > 4096):
            raise ValueError("invalid OSV page token")
        return {v["id"] for v in vulns}, token

    for start in range(0, len(packages), 500):
        chunk = packages[start : start + 500]
        queries = [
            {"package": {"ecosystem": api.osv_ecosystem(p["system"]), "name": p["name"]}, "version": p["version"]}
            for p in chunk
        ]
        try:
            results = api._post(f"{api.OSV_BASE}/querybatch", {"queries": queries}).get("results")
            if not isinstance(results, list) or len(results) != len(chunk):
                raise ValueError("OSV result count mismatch")
        except (api.ApiError, httpx.HTTPError, ValueError):
            continue
        for offset, (query, result) in enumerate(zip(queries, results)):
            ids, seen = set(), set()
            try:
                for _ in range(20):
                    page_ids, token = unpack(result)
                    ids.update(page_ids)
                    if not token:
                        output[start + offset] = {"ids": sorted(ids), "complete": True}
                        break
                    if token in seen or len(ids) > MAX_ADVISORIES or page_budget <= 0:
                        raise ValueError("OSV page limit")
                    seen.add(token)
                    page_budget -= 1
                    result = api._post(f"{api.OSV_BASE}/query", {**query, "page_token": token})
                else:
                    raise ValueError("OSV page limit")
            except (api.ApiError, httpx.HTTPError, ValueError):
                output[start + offset] = {"ids": sorted(ids) if ids else None, "complete": False}
    return output


def _metadata(package):
    try:
        system, name, version = package["system"], package["name"], package["version"]
        data = api._get(f"{api.DEPSDEV_BASE}/systems/{system}/packages/{api._q(name)}/versions/{api._q(version)}")
        api._validate_version_identity(data, system, name, version)
        advisory_keys = data.get("advisoryKeys", [])
        if not isinstance(advisory_keys, list) or any(
            not isinstance(x, dict) or not isinstance(x.get("id"), str) or not x["id"] for x in advisory_keys
        ):
            raise ValueError("invalid advisory metadata")
        return {
            "licenses": data.get("licenses"),
            "published_at": data.get("publishedAt"),
            "advisories": [x["id"] for x in advisory_keys],
            "queried": True,
        }
    except (api.ApiError, httpx.HTTPError, ValueError, TypeError):
        return {"licenses": None, "published_at": None, "advisories": [], "queried": False}


def _parallel(fn, items):
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(copy_context().run, fn, item) for item in items]
        return [future.result() for future in futures]


def evaluate_repository(data):
    gaps = list(data["inventory"]["coverage_gaps"])
    packages = data["packages"]
    outcomes, findings = [], []
    for package in packages:
        metadata, osv = package["metadata"], package["osv"]
        ids = set(osv["ids"] or []) | set(metadata["advisories"])
        groups = advisory_groups({i: data["advisories"].get(i, {}) for i in ids})
        assessment = classify_license(metadata["licenses"])
        grade = assessment["tier"] if metadata["queried"] else "conditional"
        local_gaps, local_findings = [], []
        if not osv["complete"]:
            local_gaps.append("vulnerability_query_incomplete")
        if not metadata["queried"]:
            local_gaps.append("license_query_incomplete")
        if assessment["category"] == "unknown":
            local_gaps.append("license_unverified")
        vuln_grade = "allow" if osv["complete"] else "conditional"
        for group in groups:
            score = group["score"]
            outcome = "hold" if score is not None and score >= 7 else "conditional"
            vuln_grade = max((vuln_grade, outcome), key=RANK.get)
            local_findings.append(
                {"area": "vulns", "code": "known_vulnerability", "id": group["id"], "score": score, "outcome": outcome}
            )
            if any(
                not data["advisories"].get(i)
                or data["advisories"][i].get("error")
                or data["advisories"][i].get("source_errors")
                for i in group["aliases"]
                if i in ids
            ):
                local_gaps.append("advisory_details_incomplete")
        if local_gaps:
            grade = max((grade, "conditional"), key=RANK.get)
        grade = max((grade, vuln_grade), key=RANK.get)
        target = {k: package[k] for k in ("system", "name", "version")}
        evidence = {
            "target": target,
            "lookup_package": metadata,
            "get_dependencies": {"occurrences": package["occurrences"]},
            "policy_context": data.get("policy_context"),
            "network_decisions": data.get("network_decisions", []),
        }
        verdict = {
            "policy": POLICY,
            "overall": grade,
            "areas": {"license": assessment["tier"], "vulns": vuln_grade},
            "coverage_gaps": sorted(set(local_gaps)),
            "findings": local_findings,
            "license_reviews": [
                {
                    **target,
                    "relation": "DECLARED" if target["system"] == "go" else "LOCKED",
                    "licenses": metadata["licenses"],
                    "assessment": assessment,
                }
            ],
        }
        verdict = apply_license_policy(evidence, apply_additional(evidence, verdict))
        outcomes.append({**target, "verdict": verdict})
        findings.extend({**finding, "package": target} for finding in verdict["findings"])
        gaps.extend({"code": code, "package": target} for code in verdict["coverage_gaps"])
    if not packages:
        gaps.append({"code": "no_queryable_packages"})
    grade = max(["conditional" if gaps else "allow", *(p["verdict"]["overall"] for p in outcomes)], key=RANK.get)
    ids = {i for p in packages for i in (p["osv"]["ids"] or []) + p["metadata"]["advisories"]}
    return {
        "policy": POLICY,
        "overall": grade,
        "scope": "identified_dependency_vulnerabilities_and_licenses",
        "license_data_sha256": DATA_SHA256,
        "coverage_gaps": gaps,
        "findings": findings,
        "packages": outcomes,
        "summary": {
            "projects": len(data["inventory"]["projects"]),
            "packages": len(packages),
            "vulnerability_queries_complete": sum(p["osv"]["complete"] for p in packages),
            "license_metadata_available": sum(
                p["metadata"]["queried"] and bool(p["metadata"]["licenses"]) for p in packages
            ),
            "affected_packages": sum(bool((p["osv"]["ids"] or []) + p["metadata"]["advisories"]) for p in packages),
            "advisory_groups": len(advisory_groups({i: data["advisories"].get(i, {}) for i in ids})),
            "coverage_gaps": len(gaps),
        },
    }


def collect_repository(root, output_root="reviews", public_packages=False, max_packages=2000):
    if type(max_packages) is not int or not 1 <= max_packages <= 10000:
        raise ValueError("max_packages must be 1..10000")
    inventory = discover(root, output_root)
    config = CURRENT.get()
    if public_packages is not True and not (config or {}).get("network", {}).get("allow_identifiers"):
        return {
            "error": "Inspect repo-plan locally, then confirm public package identifiers or select an explicit identifier allowlist policy.",
            "code": "public_identifiers_required",
            "network_performed": False,
        }
    packages = deepcopy(inventory["packages"])
    calls, selected = [], []
    token = api._capture.set(calls)
    try:
        for package in packages:
            package.update(
                osv={"ids": None, "complete": False},
                metadata={"licenses": None, "published_at": None, "advisories": [], "queried": False},
            )
            try:
                # Preflight individual names so a blocked private name cannot poison a public batch.
                check("osv", [identifier(package["system"], package["name"])])
                check("depsdev", [identifier(package["system"], package["name"])])
            except PolicyBlocked:
                inventory["coverage_gaps"].append(
                    {"code": "package_policy_blocked", "package": {k: package[k] for k in ("system", "name", "version")}}
                )
                continue
            if len(selected) < max_packages:
                selected.append(package)
        if len(selected) < len(packages):
            inventory["coverage_gaps"].append({"code": "packages_unqueried"})
        osv_results = _osv(selected)
        metadata = _parallel(_metadata, selected)
        for package, result, meta in zip(selected, osv_results, metadata):
            package.update(osv=result, metadata=meta)
        ids = sorted({i for p in packages for i in (p["osv"]["ids"] or []) + p["metadata"]["advisories"]})
        chosen = ids[:MAX_ADVISORIES]
        if len(chosen) < len(ids):
            inventory["coverage_gaps"].append({"code": "advisory_limit"})
        advisories = dict(zip(chosen, _parallel(lambda aid: json.loads(api._run(api._get_advisory, aid)), chosen)))
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "schema": SCHEMA,
            "generated_at": now,
            "inventory": inventory,
            "packages": packages,
            "advisories": advisories,
            "network_decisions": list(EVENTS.get() or []),
            "scope_notes": ["maintenance_not_assessed", "source_code_not_assessed", "deployment_not_assessed"],
            "limits": {"max_packages": max_packages, "max_advisories": MAX_ADVISORIES},
        }
        if config is not None:
            data["policy_context"] = {
                "schema": "oss-gate.policy-context/1",
                "config": config,
                "sha256": fingerprint(config),
                "evaluated_at": now,
            }
        if TLS_EVIDENCE.get() is not None:
            data["tls_trust"] = dict(TLS_EVIDENCE.get())
        data["verdict"] = evaluate_repository(data)
        folder = new_run(output_root, inventory["name"], "repository")
        write_json(folder / "data.json", data)
        write_json(folder / "api-responses.json", calls)
        seal(folder, ["data.json", "api-responses.json"])
        return {
            "folder": str(folder),
            "data": str(folder / "data.json"),
            "verdict": data["verdict"]["overall"],
            "summary": data["verdict"]["summary"],
        }
    finally:
        api._capture.reset(token)
