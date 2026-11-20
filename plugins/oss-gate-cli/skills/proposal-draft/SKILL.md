---
name: proposal-draft
description: Draft a practical adoption proposal from existing OSS Gate reviews or periodic reports with evidence-linked decisions, actions, measures and limitations. Supports Korean, English or both.
---

# Adoption proposal

Read the selected review and source data first. Do not invent team requirements, budgets, owners, alternatives, deployment constraints or measurements. Label a proposed requirement as a proposal and an unmeasured baseline as unmeasured.

Use explicit `--language ko|en|both` or natural-language choice; otherwise use the request language. For both, write separate complete documents using identical evidence. Translation reuses the snapshot and does not refresh it.

Write sections for context/problem, intended users, proposed adoption conditions, expected outcomes and measures, risks, evidence table, and verification. Reference exact source paths, fields, advisory IDs and version-specific findings. A policy verdict is not human approval. In particular, a license review action remains open until a human decision is recorded.

Save `proposals/<name>-<unique-id>/proposal.ko.md` and/or `proposal.en.md`, and a source manifest listing hashes and dates. Render via the plugin's `render.py --document --language <ko|en> --out <path>` using `uv run --frozen --project <plugin-root> python`. Resolve the root as `../..` from this skill.

Verify numbers, source references, unmeasured claims and language parity. If a referenced report or snapshot is missing, disclose it and do not claim the proposal is fully verified. Do not use em dashes in authored prose. Return generated paths and the unresolved decisions.
