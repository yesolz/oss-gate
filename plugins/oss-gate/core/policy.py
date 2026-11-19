"""Deterministic screening policy. Inputs are evidence, never model verdicts."""

from __future__ import annotations

import math
from .licenses import classify_license

POLICY_VERSION = "oss-gate.policy/2"
RANK = {"allow": 0, "conditional": 1, "hold": 2}
LEGACY = {"가능": "allow", "조건부": "conditional", "보류": "hold", "확인필요": "unknown", "확인 필요": "unknown"}


def obj(value):
    return value if isinstance(value, dict) else {}


def seq(value):
    return value if isinstance(value, list) else []


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def advisory_groups(advisories):
    """Union overlapping alias sets, including aliases connected through a third record."""
    groups = []
    for key, raw in obj(advisories).items():
        record = obj(raw)
        ids = {str(key)} | {
            x
            for x in [record.get("id"), record.get("canonical_id"), *seq(record.get("aliases"))]
            if isinstance(x, str) and x
        }
        merged, remaining = {"ids": ids, "records": [record]}, []
        for group in groups:
            if group["ids"] & merged["ids"]:
                merged["ids"] |= group["ids"]
                merged["records"] += group["records"]
            else:
                remaining.append(group)
        groups = remaining + [merged]
    result = []
    for group in groups:
        ids = sorted(group["ids"])
        scores = [
            r.get("cvss3_score")
            for r in group["records"]
            if number(r.get("cvss3_score")) and 0 <= r["cvss3_score"] <= 10
        ]
        records = group["records"]
        result.append(
            {
                "id": next((i for i in ids if i.startswith("GHSA-")), ids[0]),
                "aliases": ids,
                "score": max(scores) if scores else None,
                "title": next(
                    (r.get("title") or r.get("summary") for r in records if r.get("title") or r.get("summary")), ""
                ),
                "records": records,
            }
        )
    return sorted(result, key=lambda g: (-(g["score"] if g["score"] is not None else -1), g["id"]))


def evaluate(data):
    """Return stable language-neutral grades, coverage gaps, and traceable reasons."""
    lp, gd = obj(data.get("lookup_package")), obj(data.get("get_dependencies"))
    target = obj(data.get("target"))
    nodes = [obj(n) for n in seq(gd.get("nodes")) if obj(n).get("relation") != "SELF"]
    areas = {key: "allow" for key in ("license", "vulns", "deps", "maintenance")}
    gaps, findings = [], []

    def ids(value):
        if not isinstance(value, list) or any(not isinstance(v, str) or not v for v in value):
            gaps.append("invalid_advisory_ids")
        return [v for v in seq(value) if isinstance(v, str) and v]

    if any(not isinstance(target.get(k), str) or not target[k] for k in ("system", "name", "version")):
        gaps.append("invalid_target")

    def mark(area, grade, code, **detail):
        if RANK.get(grade, -1) > RANK.get(areas[area], -1):
            areas[area] = grade
        findings.append({"area": area, "code": code, **detail})

    if not lp or lp.get("error"):
        gaps.append("package_unavailable")
        areas["license"] = areas["vulns"] = "unknown"
    else:
        root_policy = classify_license(lp.get("licenses"))
        mark(
            "license",
            root_policy["tier"],
            "root_license",
            package=f"{lp.get('name')}@{lp.get('version')}",
            licenses=lp.get("licenses"),
            category=root_policy["category"],
        )
        if any(target.get(k) and target[k] != lp.get(k) for k in ("name", "version", "system")):
            gaps.append("target_mismatch")
            mark("license", "hold", "target_mismatch")

    if data.get("advisories_truncated"):
        gaps.append("advisories_truncated")
    graph_matches = (
        bool(gd)
        and not gd.get("error")
        and not gd.get("fallback_used")
        and (gd.get("resolved_version") or gd.get("version")) == target.get("version")
    )
    if not graph_matches:
        gaps.append("graph_version_unverified")
        areas["deps"] = "unknown"
    roots = [obj(n) for n in seq(gd.get("nodes")) if obj(n).get("relation") == "SELF"]
    if (
        len(roots) != 1
        or roots[0].get("name") != target.get("name")
        or roots[0].get("version") != target.get("version")
    ):
        gaps.append("graph_root_unverified")
        graph_matches = False
        areas["deps"] = "unknown"
    if any(not n.get("name") or not n.get("version") or n.get("relation") not in ("DIRECT", "INDIRECT") for n in nodes):
        gaps.append("graph_node_unverified")
    for flag in ("truncated", "osv_incomplete", "graph_error", "nodes_with_errors", "license_lookup_failures"):
        if gd.get(flag):
            gaps.append(flag)
    if not seq(gd.get("nodes")):
        gaps.append("graph_empty")
    for node in nodes:
        if node.get("vulns_queried") is not True or node.get("vuln_count") is None:
            gaps.append("dependency_vulnerabilities_unqueried")
        elif not isinstance(node.get("vuln_ids"), list) or node["vuln_count"] != len(node["vuln_ids"]):
            gaps.append("dependency_advisory_count_mismatch")
        if node.get("licenses_queried") is not True or node.get("license_error"):
            gaps.append("dependency_license_unqueried")
        elif graph_matches:
            lic = classify_license(node.get("licenses"))
            if lic["tier"] != "allow":
                mark(
                    "license",
                    lic["tier"],
                    "dependency_license",
                    package=f"{node.get('name')}@{node.get('version')}",
                    licenses=node.get("licenses"),
                    category=lic["category"],
                    path=node.get("path"),
                )
    groups = advisory_groups(data.get("advisories"))
    id_groups = {alias: group for group in groups for alias in group["aliases"]}
    root_osv = obj(data.get("root_osv"))
    root_ids = list(dict.fromkeys(ids(lp.get("advisories")) + (ids(root_osv.get("ids")) if root_osv else [])))
    if data.get("schema") == "oss-gate.review/2" and (
        root_osv.get("queried") is not True or root_osv.get("incomplete")
    ):
        gaps.append("root_osv_unavailable")
    if lp and not lp.get("error") and not isinstance(lp.get("advisories"), list):
        gaps.append("root_vulnerabilities_unqueried")
    for area, advisory_ids in [
        ("vulns", root_ids),
        ("deps", [i for n in nodes for i in ids(n.get("vuln_ids"))] if graph_matches else []),
    ]:
        seen = set()
        for aid in advisory_ids:
            group = id_groups.get(aid)
            if group is None or group["score"] is None:
                gaps.append("advisory_severity_unknown")
                mark(area, "conditional", "severity_unknown", advisory=aid)
            elif group["id"] not in seen:
                seen.add(group["id"])
                mark(
                    area,
                    "hold" if group["score"] >= 7 else "conditional",
                    "known_vulnerability",
                    advisory=group["id"],
                    score=group["score"],
                )
    sc = obj(obj(data.get("get_project")).get("scorecard"))
    score = sc.get("overall")
    maintained = next((c.get("score") for c in seq(sc.get("checks")) if obj(c).get("name") == "Maintained"), None)
    if number(maintained) and maintained == 0:
        mark("maintenance", "hold", "unmaintained")
    elif number(score) and 0 <= score <= 10:
        mark(
            "maintenance",
            "allow" if score >= 7 else "conditional" if score >= 4 else "hold",
            "scorecard",
            score=score,
            date=sc.get("date"),
        )
    else:
        areas["maintenance"] = "unknown"
        findings.append({"area": "maintenance", "code": "maintenance_unavailable"})
    overall = max((v for v in areas.values() if v in RANK), key=RANK.get, default="conditional")
    if gaps and overall == "allow":
        overall = "conditional"
    if obj(data.get("verification")).get("status") == "FAIL":
        overall = "hold"
        findings.append({"area": "overall", "code": "verification_failed"})
    return {
        "policy": POLICY_VERSION,
        "overall": overall,
        "areas": areas,
        "coverage_gaps": sorted(set(gaps)),
        "findings": findings,
        "advisory_count": len(groups),
        "high_critical_count": sum(g["score"] is not None and g["score"] >= 7 for g in groups),
        "severity_unknown_count": sum(g["score"] is None for g in groups),
    }
