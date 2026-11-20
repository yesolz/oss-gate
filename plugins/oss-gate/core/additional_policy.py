"""Optional, monotonic rules evaluated against saved evidence and a fixed clock."""

from datetime import datetime, timezone
from fnmatch import fnmatchcase
import re
from urllib.parse import urlsplit

from .settings import fingerprint, validate


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp requires timezone")
    try:
        return parsed.astimezone(timezone.utc)
    except OverflowError as exc:
        raise ValueError("timestamp is outside the supported UTC range") from exc


def public_url(value, schemes=("https",)):
    if not isinstance(value, str):
        return False
    try:
        p = urlsplit(value)
        if p.hostname:
            p.hostname.rstrip(".").encode("idna")
        if p.port is not None and not 1 <= p.port <= 65535:
            return False
        return (
            p.scheme in schemes
            and bool(p.hostname)
            and not any(c in p.hostname for c in ("%", "\\"))
            and not p.username
            and not p.password
            and not re.search(r"[\x00-\x20\x7f]", value)
        )
    except ValueError:
        return False


def validate_communication(value):
    """Validate reviewer-supplied facts; this does not independently verify them."""
    if not isinstance(value, dict) or value.get("schema") != "oss-gate.communication/1":
        raise ValueError("unsupported communication evidence schema")
    if set(value) - {"schema", "target", "status", "coverage", "reviewed_by", "reviewed_at", "sources", "observations"}:
        raise ValueError("unknown communication evidence field")
    if value.get("status") not in ("unverified", "reviewed") or value.get("coverage") not in ("partial", "complete"):
        raise ValueError("invalid communication review status or coverage")
    target = value.get("target")
    if (
        not isinstance(target, dict)
        or set(target) != {"system", "name", "version"}
        or any(not isinstance(v, str) or not v for v in target.values())
    ):
        raise ValueError("communication evidence requires an exact target")
    sources = value.get("sources", [])
    if not isinstance(sources, list) or len(sources) > 100 or any(not public_url(s) for s in sources):
        raise ValueError("communication sources must be HTTPS URLs without credentials")
    if value["status"] == "reviewed":
        if not sources or not isinstance(value.get("reviewed_by"), str) or not value["reviewed_by"].strip():
            raise ValueError("reviewed evidence requires sources and reviewer attribution")
        timestamp(value.get("reviewed_at"))
    observations = value.get("observations")
    if not isinstance(observations, list) or len(observations) > 200:
        raise ValueError("invalid communication observations")
    for item in observations:
        if not isinstance(item, dict) or set(item) != {
            "destination",
            "data",
            "purpose",
            "default_enabled",
            "required",
            "can_disable",
        }:
            raise ValueError("invalid communication observation fields")
        if not public_url(item["destination"], ("https", "http")) or any(
            not isinstance(item[k], str) or not item[k] for k in ("data", "purpose")
        ):
            raise ValueError("observations require a destination, data description and purpose")
        if any(
            item[k] is not None and type(item[k]) is not bool for k in ("default_enabled", "required", "can_disable")
        ):
            raise ValueError("communication flags must be boolean or null")
    return value


def apply(data, base):
    context = data.get("policy_context")
    if context is None:
        return base
    if not isinstance(context, dict) or context.get("schema") != "oss-gate.policy-context/1":
        raise ValueError("invalid saved policy context")
    config = validate(context.get("config"))
    if fingerprint(config) != context.get("sha256"):
        raise ValueError("saved policy fingerprint mismatch")
    clock = timestamp(context.get("evaluated_at"))
    rules = config.get("review", {})
    findings, gaps = [], []

    def finding(code, outcome="conditional", **detail):
        findings.append({"area": "additional", "code": code, "outcome": outcome, **detail})

    days = rules.get("minimum_release_age_days", 0)
    if days:
        try:
            published = timestamp(data.get("lookup_package", {}).get("published_at"))
            seconds = (clock - published).total_seconds()
            if seconds < 0:
                raise ValueError("future publication")
            if seconds < days * 86400:
                finding(
                    "release_wait",
                    minimum_days=days,
                    age_days=round(seconds / 86400, 3),
                    published_at=published.isoformat(),
                )
        except (ValueError, TypeError, OverflowError):
            gaps.append("release_time_unverified")
            finding("release_time_unverified")

    require = rules.get("require_communication_review", False)
    blocked = rules.get("blocked_destinations", [])
    if require or blocked:
        facts = data.get("communication")
        usable = False
        try:
            validate_communication(facts)
            usable = (
                facts["status"] == "reviewed"
                and facts["target"] == {k: data["target"][k] for k in ("system", "name", "version")}
                and timestamp(facts["reviewed_at"]) <= clock
            )
        except (ValueError, KeyError, TypeError):
            pass
        if not usable or facts.get("coverage") != "complete":
            gaps.append("communication_unverified")
            finding("communication_unverified")
        if usable:
            if require and any(
                item[k] is None
                for item in facts["observations"]
                for k in ("default_enabled", "required", "can_disable")
            ):
                gaps.append("communication_configuration_unverified")
                finding("communication_configuration_unverified")
            for item in facts.get("observations", []):
                host = urlsplit(item["destination"]).hostname.rstrip(".").encode("idna").decode("ascii")
                if any(fnmatchcase(host, pattern) for pattern in blocked):
                    if item["required"] is True or item["default_enabled"] is True:
                        finding(
                            "blocked_destination", "hold", destination=item["destination"], sources=facts["sources"]
                        )
                    elif item["required"] is None or item["default_enabled"] is None:
                        gaps.append("communication_configuration_unverified")
                        finding("communication_configuration_unverified", destination=item["destination"])
    network_events = data.get("network_decisions", [])
    if any(event.get("decision") == "blocked" for event in network_events):
        gaps.append("policy_limited_collection")
        finding("policy_limited_collection")
    rank = {"allow": 0, "conditional": 1, "hold": 2}
    outcome = max([base["overall"], *(f["outcome"] for f in findings)], key=rank.get)
    return {
        **base,
        "overall": outcome,
        "coverage_gaps": sorted(set(base["coverage_gaps"] + gaps)),
        "findings": base["findings"] + findings,
        "additional_policy": {
            "name": config["name"],
            "version": config["version"],
            "sha256": context["sha256"],
            "evaluated_at": context["evaluated_at"],
            "base_overall": base["overall"],
            "overall": outcome,
            "findings": findings,
        },
    }
