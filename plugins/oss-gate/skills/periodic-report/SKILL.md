---
name: periodic-report
description: Produce a periodic portfolio report from existing OSS Gate reviews, comparing versions, verdicts, vulnerabilities, licenses and outstanding actions. Supports Korean, English or both without silently refreshing evidence.
---

# Periodic report

Use local review snapshots supplied by the user. Select the newest snapshot for each exact ecosystem/name/version within the requested interval; list excluded or missing snapshots. Never merge distinct versions or treat a missing prior report as zero.

Run `uv run --frozen --project "<plugin-root>" python "<plugin-root>/portfolio.py" <selected data.json paths> --out <new summary.json>` for numerical aggregation. The shared `core.portfolio.compare` function compares exact targets under the same policy. Never calculate portfolio totals in prose alone. Recompute all compared snapshots with the same policy, and disclose any difference from historical verdicts. Compare like-for-like targets and distinguish newly collected evidence from historical snapshots. Do not run new reviews unless requested.

Explicit `--language ko|en|both` or natural-language choice wins; otherwise use the request language. Both languages share the same input list, hashes and computed totals.

Save `reports/<period>-<unique-id>/summary.json` with selected source paths, SHA-256 hashes, exclusions, counts and policy version, plus `report.ko.md` and/or `report.en.md`. Explain summary, target table, changes, actions, unknowns and verification. Every action needs a source. Missing source files are visible limitations; never claim PASS for unavailable evidence.

To render each Markdown document:
`uv run --frozen --project "<plugin-root>" python "<plugin-root>/render.py" "<report.md>" --document --language en --out "<report.en.html>"`

Resolve plugin-root from this skill (`../..`). Check source hashes, counts, deduplicated advisory IDs, dates and bilingual parity before delivery. Do not use em dashes in authored prose. Report output paths and material gaps.
