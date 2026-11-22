# Local policy/3 validation

This record covers local validation on 2026-11-22 before the changes were committed and pushed. No release was published. Remote CI results are reported separately by GitHub Actions.

## Results

- Python 3.10 and 3.13 each passed 119 unittest tests, including expression precedence, selected OR branches, malformed alternatives, distinct uncertainty reasons, exact restrictions, evidence-bound acceptance, expired/future/nonmatching decisions, escaped HTML, offline reassessment, preserved verification failures and equivalent PyPI graph versions.
- Ruff, both MCP adapters, generated CLI parity, bilingual examples, 20 static pages and distribution checks passed locally. These runs do not establish Windows/Linux CI results for this candidate.
- Real deps.dev lookups reproduced the six feedback examples: unicode-ident 1.0.27, pillow 13.0.0 and webpki-roots 1.0.12 classify as permissive; caniuse-lite 1.0.30001826 requires attribution review; certifi 2026.11.20 and tqdm 4.70.1 remain weak-copyleft/conditional. These are license results, not whole-package approvals.
- The fresh packaging 26.3 example returned allow with no custom settings. Original API responses and a local integrity manifest are included. Its Scorecard is dated 2026-08-24 and remains identified as older evidence.
- The historical Next 16.4.6 example changes from policy/2 hold to policy/3 conditional. Next 15.1.0 remains hold, Requests remains conditional, and FastAPI still has incomplete dependency coverage. The original historical data files were not modified.
- Aside inspection covered Korean/English report previews and the user-decision section. README images are cropped screenshots of actual report output, excluding browser chrome and unrelated tabs.

Gitleaks found one default-rule false positive: the SHA-256 of `api-responses.json` in its integrity manifest. The narrow repository configuration matches that exact manifest entry shape only. The extracted candidate then passed; synthetic key controls in ordinary source and another manifest field were both still detected. No evidence was changed to suppress the warning.

## Evidence-recording follow-up

- A live `explain jonschlinkert/is-odd --topic overview` returned `isError: true` with Repository not found. The CLI saved the unchanged remote content with tool-recorded UTC time, and still exited 1.
- A fresh is-odd 3.0.1 collection, explanation index, agent check and both HTML languages completed through the bundled CLI. The verdict remained hold for maintenance; missing DeepWiki coverage was recorded as unresolved with verification WARN. These private test narratives are not presented as new public showcase reports.
- The new checks cover successful/error/local-failure captures, no-overwrite behavior, index paths/topics/repositories, stale evidence/narrative/translation detection, explicit archived rechecks, legacy compatibility and sealed FAIL preservation. Supplied timestamps and contradictory PASS inputs are rejected.
- A clean temporary Python 3.13 environment installed the frozen runtime with `uv sync --frozen --no-cache`, including pydantic 2.14.4. This confirms the tested public artifact path, not availability in someone else's mirror. No dependency pins changed.
- The additional is-odd HTML files passed generation, but a new Aside visual inspection could not run because the Mac was locked. The earlier bilingual layout inspection remains separate evidence.

## Agent journey

A temporary local marketplace installed the candidate in Codex 0.163.0-alpha.11. The successful run explicitly selected the candidate installation, used the bundled CLI for collection and the local stdio DeepWiki adapter for explanation, and generated Korean/English Markdown and HTML from one sealed snapshot. The maintainer checked source hashes and recomputed the policy. Verification remains WARN for unverified communication and version-specific narrative limitations. The temporary plugin and marketplace were removed after the test.

The first attempt selected an existing installation and stopped at runtime bootstrap in a network-restricted session. A second attempt explicitly selected the candidate, permitted its locked runtime dependencies and enabled network access for that session. This is a bounded noninteractive CLI journey, not a test of every interactive host permission flow.

Claude Code 2.1.212 accepted the candidate manifest. Its model-driven review attempt stopped with HTTP 401 because the existing OAuth token had expired, before any model inference. Reauthentication is required before claiming the complete Claude journey passes. Local protocol tests are not a substitute for that run.

No third-party runtime package/version pins changed. Formatting/import checks and annotations were focused on the changed license modules; a repository-wide type-checking migration was not added. No external testers were contacted. Use [the first-use checklist](first-use-check.md) for two or three independent first-time users before claiming external usability validation.

Local transcripts, detailed test logs, live lookup evidence and source hashes are retained in ignored `verification-local/policy3/`. They are not distributed as private validation transcripts. The public packaging example contains only selected public API evidence and its explanatory narrative.
