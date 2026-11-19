"""Deterministic aggregation of saved reviews with explicit exclusions."""

from __future__ import annotations
import argparse
from datetime import datetime
from pathlib import Path

from .policy import POLICY_VERSION, advisory_groups, evaluate
from .snapshot import load_review, sha256, write_json


def aggregate(paths):
    selected, excluded = {}, []
    for input_path in paths:
        path = Path(input_path)
        if path.is_dir():
            path = path / "data.json"
        try:
            data = load_review(path)
            target = data["target"]
            key = tuple(target[k] for k in ("system", "name", "version"))
            if any(not isinstance(v, str) or not v for v in key):
                raise ValueError("invalid target")
            timestamp = datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                raise ValueError("timestamp requires timezone")
            previous = selected.get(key)
            if previous and timestamp <= previous[0]:
                excluded.append({"path": str(path), "reason": "older_or_duplicate_snapshot"})
                continue
            if previous:
                excluded.append({"path": str(previous[1]), "reason": "superseded_snapshot"})
            selected[key] = (timestamp, path, data)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            excluded.append(
                {"path": str(path), "reason": "missing_invalid_or_changed_evidence", "error_type": type(exc).__name__}
            )
    items, all_advisories = [], {}
    counts = {"allow": 0, "conditional": 0, "hold": 0}
    for key in sorted(selected):
        _, path, data = selected[key]
        verdict = evaluate(data)
        counts[verdict["overall"]] += 1
        groups = advisory_groups(data.get("advisories"))
        # Duplicate records merge by their actual alias identities, not package counts.
        for group in groups:
            previous = all_advisories.get(group["id"], {})
            scores = [v for v in (previous.get("cvss3_score"), group["score"]) if v is not None]
            all_advisories[group["id"]] = {
                "id": group["id"],
                "aliases": sorted(set(previous.get("aliases", [])) | set(group["aliases"])),
                "cvss3_score": max(scores) if scores else None,
            }
        items.append(
            {
                "target": data["target"],
                "path": str(path),
                "sha256": sha256(path),
                "generated_at": data["generated_at"],
                "verdict": verdict,
            }
        )
    groups = advisory_groups(all_advisories)
    return {
        "schema": "oss-gate.portfolio/1",
        "policy": POLICY_VERSION,
        "items": items,
        "excluded": excluded,
        "counts": counts,
        "review_count": len(items),
        "unique_advisory_groups": len(groups),
        "high_critical_groups": sum(g["score"] is not None and g["score"] >= 7 for g in groups),
        "complete": bool(items) and not excluded and not any(i["verdict"]["coverage_gaps"] for i in items),
    }


def compare(current, previous):
    """Compare exact targets under the same policy; absent items are not zero findings."""
    if current.get("policy") != previous.get("policy"):
        raise ValueError("recompute both portfolios with the same policy before comparing")

    def indexed(portfolio):
        return {tuple(i["target"][k] for k in ("system", "name", "version")): i for i in portfolio["items"]}

    now, before = indexed(current), indexed(previous)
    rows = []
    for key in sorted(set(now) | set(before)):
        old, new = before.get(key), now.get(key)
        rows.append(
            {
                "target": dict(zip(("system", "name", "version"), key)),
                "status": "comparable" if old and new else "new_target" if new else "missing_current_target",
                "previous": old["verdict"]["overall"] if old else None,
                "current": new["verdict"]["overall"] if new else None,
            }
        )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="+", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.out, aggregate(args.sources))


if __name__ == "__main__":
    main()
