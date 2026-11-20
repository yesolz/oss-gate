# Changelog

## 0.3.0

- Share collection and policy functions between thin MCP adapters and a local CLI; preserve default review behavior.
- Support explicitly selected outbound rules and additive release-age/communication review conditions, with sealed policy provenance and a fixed evaluation clock.
- Route DeepWiki through a lazy local adapter with fixed public-software questions and the same outbound checks.
- Explain optional policy results in Korean and English reports and reject mixed-policy portfolio comparisons.

## 0.2.3

- Show opening recommendations and readable analysis before detailed data, preserving quoted summaries, reference links and source context.
- Distinguish supplemental analysis from automated verdicts and explain the verdict levels.
- Shorten report-writing guidance around the decision, its reason and the next action; refresh bilingual example HTML.
- Keep review context available in print output and compact verdict information on narrow screens.

## 0.2.2

- Preserve unknown CVSS v3 severity when an upstream advisory supplies a zero score without a valid zero-impact vector. Recover scores from valid vectors and reject out-of-range scores.
- Add regression coverage and record real Codex adoption-review validation.

## 0.2.1

- Explain deps.dev package/version misses with bounded npm/PyPI public-registry existence checks, without substituting review evidence or approving missing data.
- Retry transient read failures once, honor short Retry-After delays, and leave long waits and unresolved lookups explicit.

- Reject upstream redirects as failed lookups, including JSON bodies that resemble successful OSV results.
- Derive release archive names from the plugin version.

## 0.2.0

- Package OSS Gate for Claude Code and Codex with shared MCP, skills, policy and renderer.
- Replace the hosted review runtime with a read-only static demo; exclude the workshop deployment configuration from the public distribution and history.
- Add MIT licensing, source attribution, contribution/security guidance and release checks.
- Support Korean, English and both, with snapshot-preserving translation and bilingual historical examples.
- Capture original public API JSON and normalized evidence directly with integrity hashes and unique run directories.
- Compute verdicts in code and preserve missing, failed, capped and mismatched evidence as uncertainty.
- Stop treating version ranges as installed versions and fixed releases as remediation of an older vulnerable version.
- Harden license classification and escape report content; remove remote font dependencies and broad global hooks.
- Add offline regressions, MCP protocol/live checks, independent dependency auditing and static-distribution validation.

The revised examples do not alter their source JSON. FastAPI's substituted graph now limits its outcome to conditional; the missing Flask source is excluded from portfolio totals. This release does not certify the historical claims or retire any live cloud resources automatically.
