# Python web library portfolio: November 2026

Snapshot date: 2026-11-17 · Example revision: policy v3 · Verification: **WARN**

> This revises a historical periodic report for publication. Its original list contained Flask and Requests, but this repository does not contain Flask's source snapshot. One verifiable item and one unverified item are kept separate. No new API query is performed.

## 1. Summary

The available snapshot covers Requests 2.34.2. Recalculation under policy v3 gives allow 0, conditional 1 and hold 0. Flask 3.1.3 is separately excluded because its evidence is missing. The Requests snapshot has 0 known advisory records; that does not establish the safety of the complete original list, including Flask.

The outstanding Requests adoption question is certifi@2026.10.23 and its MPL-2.0 license. A human must review the actual modifications and distribution. There is no previous periodic report to calculate a change from.

## 2. Targets and scope

| Package | Version | Revised example verdict | Evidence | Status |
|---|---|---|---|---|
| pypi/requests | 2.34.2 | Conditional | [data.json](../reviews/psf-requests-2.34.2/data.json) | Snapshot available |
| pypi/flask | 3.1.3 | Unverified | Mentioned in the old document only | Source missing; excluded from totals |

The old document said Flask's itsdangerous@2.2.0 and jinja2@3.1.6 were classified as `non-standard`. Without the original JSON, that claim is not included in current totals or presented as independently verified fact.

## 3. Available findings

Requests has 4 direct and 0 transitive dependencies in the saved graph. The graph was not truncated and did not use a fallback version. certifi@2026.10.23 has MPL-2.0, charset-normalizer@3.5.2 MIT, idna@3.20.0 BSD-3-Clause, and urllib3@2.8.0 MIT.

Its Scorecard is 8.2, dated 2026-08-24, which was 85 days before the original review. Because Flask's evidence is absent, the old two-package average of 7.65 is not reused as a currently verified average.

## 4. Actions

| Target | Required action | Evidence |
|---|---|---|
| Requests | Record a human decision about certifi modifications, distribution and MPL-2.0 obligations. | `get_dependencies.non_permissive` |
| Requests | Compare the actual lockfile with all four dependency versions and refresh evidence before a production decision. | `get_dependencies.nodes`, `generated_at` |
| Flask | Recover the original snapshot or request a fresh review. Do not approve it from the old prose alone. | Missing evidence |

## 5. Limitations and verification

Verification is WARN. Requests evidence and recalculation can be checked, but Flask's source and a previous comparison period are unavailable. The old document's PASS label is not inherited by this revised example. Zero known advisories is not a security guarantee, and DeepWiki explanations are AI-generated and not version-pinned.

Sources are the [Requests English review](../reviews/psf-requests-2.34.2/review.en.md), [original snapshot](../reviews/psf-requests-2.34.2/data.json), and [snapshot hashes](../snapshot-sha256.json). This document does not replace legal interpretation or organizational approval.
