"""Optional license restrictions and attributed decisions, never automatic approval."""

import hashlib
import json

from .licenses import IDS, RANK, classify_license


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def validate_rules(review: dict) -> None:
    restrictions = review.get("license_restrictions", {})
    if not isinstance(restrictions, dict) or len(restrictions) > 200:
        raise ValueError("invalid license restrictions")
    for key, value in restrictions.items():
        if key not in IDS.values() or value not in ("conditional", "hold"):
            raise ValueError("license restrictions require exact SPDX IDs and conditional or hold")
    decisions = review.get("license_decisions", [])
    if not isinstance(decisions, list) or len(decisions) > 200:
        raise ValueError("invalid license decisions")
    from .additional_policy import timestamp

    seen = set()
    for item in decisions:
        required = {"finding_sha256", "decided_by", "decided_at", "reason", "conditions"}
        if not isinstance(item, dict) or not required <= item.keys() or set(item) - required - {"expires_at"}:
            raise ValueError("invalid license decision fields")
        for key in required:
            if not isinstance(item[key], str) or not item[key].strip() or len(item[key]) > 2000:
                raise ValueError("license decisions require bounded nonempty strings")
        key = item["finding_sha256"]
        if len(key) != 64 or any(c not in "0123456789abcdef" for c in key) or key in seen:
            raise ValueError("invalid or duplicate license finding hash")
        seen.add(key)
        decided = timestamp(item["decided_at"])
        if "expires_at" in item and timestamp(item["expires_at"]) <= decided:
            raise ValueError("license decision expiry must follow decision time")


def apply_license_policy(data: dict, verdict: dict) -> dict:
    from .additional_policy import timestamp

    context = data.get("policy_context") or {}
    rules = context.get("config", {}).get("review", {})
    restrictions = rules.get("license_restrictions", {})
    evidence = digest({key: data.get(key) for key in ("target", "lookup_package", "get_dependencies")})
    reviews = []
    for item in verdict.get("license_reviews", []):
        assessment = classify_license(item["licenses"], restrictions)
        entry = {**item, "assessment": assessment}
        entry["finding_sha256"] = digest({"evidence": evidence, "policy": verdict["policy"], **entry})
        reviews.append(entry)
    findings = list(verdict["findings"])
    restriction_findings = []
    license_grade = verdict["areas"]["license"]
    for old, new in zip(verdict.get("license_reviews", []), reviews):
        if RANK[new["assessment"]["tier"]] > RANK[old["assessment"]["tier"]]:
            finding = {
                "area": "license",
                "code": "selected_license_restriction",
                "outcome": new["assessment"]["tier"],
                **new,
            }
            findings.append(finding)
            restriction_findings.append(finding)
            license_grade = max((license_grade, new["assessment"]["tier"]), key=lambda x: RANK.get(x, -1))
    overall = max((verdict["overall"], license_grade), key=lambda x: RANK.get(x, -1))
    verdict = {
        **verdict,
        "overall": overall,
        "areas": {**verdict["areas"], "license": license_grade},
        "findings": findings,
        "license_reviews": reviews,
    }
    if verdict.get("additional_policy"):
        verdict["additional_policy"] = {
            **verdict["additional_policy"],
            "overall": overall,
            "findings": verdict["additional_policy"]["findings"] + restriction_findings,
        }
    if rules.get("license_decisions"):
        clock = timestamp(context["evaluated_at"])
        eligible = {item["finding_sha256"]: item for item in reviews if item["assessment"]["tier"] != "allow"}
        decisions = []
        for decision in rules["license_decisions"]:
            key = decision["finding_sha256"]
            status = "recorded"
            if key not in eligible:
                status = "not_matching"
            elif eligible[key]["assessment"]["category"] == "unknown":
                status = "evidence_unresolved"
            elif timestamp(decision["decided_at"]) > clock:
                status = "future_decision"
            elif decision.get("expires_at") and timestamp(decision["expires_at"]) <= clock:
                status = "expired"
            decisions.append({**decision, "status": status})
        accepted = sum(item["status"] == "recorded" for item in decisions)
        verdict["license_decisions"] = {
            "items": decisions,
            "recorded": accepted,
            "pending": len(eligible) - accepted,
            "total": len(eligible),
        }
    return verdict
