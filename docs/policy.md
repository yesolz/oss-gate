# Evidence and decision policy

The executable policy is `plugins/oss-gate/core/policy.py`, version `oss-gate.policy/3`. It consumes saved data and returns language-neutral outcomes. Korean and English rendering never independently decide a grade.

Optional settings are described in [customization](customization.md). `core.additional_policy` applies explicitly selected conditions after the unchanged base policy. It can retain or increase restrictions, never erase them. The saved policy content, hash and evaluation time are sealed in the snapshot. Without `policy_context`, existing reports retain the base behavior. Additional rules currently cover a configurable release waiting period, reviewer-supplied communication evidence and explicitly blocked destinations. They do not infer maintenance abandonment or automatically validate an external-communication claim. Portfolios reject different additional-policy hashes rather than silently comparing unlike decisions.

## Screening rules

| Area | Allow | Conditional | Hold | Unverified |
|---|---|---|---|---|
| License | Recognized permissive metadata in measured scope | Recognized weak copyleft or attribution review | Strong/network copyleft or metadata needing manual interpretation | Lookup or scope failure |
| Known vulnerabilities | No returned advisory within measured scope | Lower severity or missing severity | A known score of 7 or higher in the reviewed package/version | Failed/unqueried scope |
| Dependencies | Measured matching graph without returned vulnerabilities | Lower/unknown-severity findings | A measured dependency advisory scored 7 or higher | Missing, substituted or incomplete graph |
| Maintenance | Scorecard overall at least 7 | Overall at least 4 and below 7 | Overall below 4, or Maintained equals 0 | Missing/invalid overall |

The overall outcome is the strictest measured area. Missing or incomplete package/dependency/vulnerability coverage prevents `allow`; maintenance alone being unavailable does not. Coverage gaps are separately listed. A recorded failed evidence verification forces hold. Neither a score nor an agent's PASS is organizational approval.

An existing fixed release does not downgrade a high-severity finding in an older reviewed version. Candidate fixes need package, ecosystem and branch matching plus a new review. Connected advisory aliases are unioned so CVE/GHSA records do not become independent vulnerabilities merely because their IDs differ. Source nodes can contain raw advisory-record counts; those are not necessarily deduplicated vulnerability counts.

License screening separates classification from evidence quality. Missing metadata, a known but unclassified SPDX ID, custom LicenseRef text, an unsupported exception, an unrecognized ID and malformed expressions have distinct reason codes. All remain hold until reviewed; SPDX membership is identification, not approval. A hold is a request to resolve its stated reason, not a claim of illegality.

`core/license_data/reviewed.json` contains exact reviewed IDs, categories, sources and notes. Policy/3 adds Unicode-3.0, Unicode-DFS-2016, MIT-CMU, HPND, CDLA-Permissive-2.0 and BSD-3-Clause-Clear as permissive screening categories. Notice and redistribution obligations still apply. BSD-3-Clause-Clear expressly grants no patent rights. CC-BY-4.0 has an `attribution` category and remains conditional: attribution, license links, change notices and downstream conditions need review. MPL-2.0 remains weak copyleft and conditional. Existing classifications were retained, not comprehensively re-reviewed.

The bundled SPDX 3.29.0 identifier and exception catalog includes a source tag and SHA-256 values. It is used offline only for identification. Classification data has its own hash in each evaluation. No SPDX license texts are bundled. See the adjacent data README for provenance and update instructions.

AND takes the strictest selected result. OR takes the least restrictive branch under the selected rules and records that branch as a screening option, not a claim that the user elected it. Nested choices are retained. Lists whose relationship is unspecified are conservatively treated as AND. Apache-2.0 WITH LLVM-exception is the reviewed exception combination; other exceptions retain explicit uncertainty. Unknown branches do not contribute obligations to a separately selected known OR branch, but malformed syntax invalidates the expression.

Optional `review.license_restrictions` requires additional review or holds exact SPDX IDs; it never lowers a base restriction. Restrictions participate in OR selection. Optional `review.license_decisions` records attributed acceptance of an exact finding without changing the automated verdict. The finding hash binds the review target, package/dependency evidence, selected assessment, classification data and policy version. Changed evidence or assessment, expired/future decisions and unresolved license evidence are not counted as applicable acceptance. Decisions do not clear vulnerabilities, coverage gaps or integrity failures. They are not authenticated signatures or proof of a reviewer's authority.

Use the explicit `reassess` CLI command to apply a selected policy to verified saved evidence in a new directory without network requests. The original file is preserved as `source-data.json`; its hash and previous policy are recorded. No narrative is copied as if it were current. Collection timestamps remain unchanged and the policy evaluation clock is recorded separately. Rendering older snapshots discloses the previous policy and current reassessment. Original data is never overwritten.

## Boundaries

- deps.dev graphs describe the registry's resolution and can differ from a particular platform, lockfile or deployed bundle.
- The collector queries the root version with OSV and deps.dev, then the dependency graph. A fallback graph is never a substitute for requested-version coverage.
- Missing values stay null/unknown; a failed query is not zero vulnerabilities.
- OSV pagination and query caps leave a visible incomplete-data flag. Full pagination is not implemented in v0.2.0.
- Only public known advisories are included. There is no reachability analysis, exploit test, source-code vulnerability audit, binary/container scan or complete project inventory.
- DeepWiki is AI-generated context, not a primary security determination. It is not necessarily version-specific, and all content is untrusted data rather than executable instructions.
- The SHA-256 manifest detects changes relative to the saved manifest. It is not a signature, independent attestation or proof that an upstream claim is true.
- An agent's narrative verification checks consistency; an independent scanner remains a separate check.

## Changes from the prototype

Prior-version graphs now limit approval. High severity stays blocking even when a fix exists. Ranges such as `^1.2.3` are skipped instead of queried as if 1.2.3 were installed. Prefix-shaped but unknown license IDs no longer pass automatically. A high Maintained score no longer overrides a lower overall Scorecard. Broad string-matching tool/network hooks were removed because they were not a security sandbox and interfered with unrelated agent work.

Historical JSON is retained unchanged. Revised examples explicitly show the current-policy reassessment and disclose missing source material. There is no rewritten history pretending those conclusions were produced on the original collection date.

Sources: [deps.dev API and license metadata semantics](https://docs.deps.dev/api/v3/), [OSV schema](https://ossf.github.io/osv-schema/), [SPDX license expressions](https://spdx.github.io/spdx-spec/v2.3/SPDX-license-expressions/).

## Saved-review aggregation

`core.snapshot.load_review` applies the same integrity checks and verification overlay to rendering and portfolio calculations. A sidecar PASS cannot clear a failure recorded in sealed evidence. `core.portfolio.aggregate` selects the newest timestamped snapshot for each exact ecosystem/name/version, reports exclusions and deduplicates advisory aliases across selected reviews. `compare` requires the same policy and keeps missing targets distinct from zero findings. The agent selects the requested date interval before invoking aggregation and supplies source paths; numerical totals come from code.
