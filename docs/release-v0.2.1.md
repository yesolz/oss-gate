# v0.2.1 validation record

Reviewed on 2026-11-20 (Asia/Seoul). This patch improves lookup diagnostics and transient failure handling. It adds no dependencies, service accounts or hosted runtime.

## Review outcome

- A deps.dev HTTP 404 triggers at most two distinct public npm/PyPI registry URLs. Package absence, version absence, registry-confirmed existence and unverified existence remain distinct.
- Registry metadata must identify the requested target. Redirects, mismatched metadata, authorization failures and unavailable registries do not establish absence. Other ecosystems and private registries remain unchecked.
- Existence checks never replace license or vulnerability evidence. A failed initial lookup cannot create a review directory or an approval.
- Transient requests retry at most once. Short Retry-After delays are honored; waits over two seconds stop automatic retries. This is a per-request bound, not a deadline for the entire review.
- Final review found that JSON-bearing redirects could pass the shared upstream parser. The parser now rejects non-2xx responses; a regression verifies that redirected OSV data cannot become a clean vulnerability result.
- Release filenames now follow the plugin manifest. Distribution validation checks agreement between runtime, project, marketplace and plugin versions.

## Verification

- All 37 unittest methods pass locally, including the retained 177 legacy assertions. Tests cover successful retries, permanent failures, malformed data, scoped npm names, normalized PyPI names and false-approval prevention.
- Ruff correctness checks, formatting of changed Python logic, Git whitespace checks and static distribution validation pass. The bilingual demo has 18 HTML pages with local links and no live input forms.
- The MCP stdio server initializes and exposes six tools. Live deps.dev and OSV calls, evidence collection with hash verification, non-approval of a vulnerable Requests version, and DeepWiki discovery/reading pass.
- The locked Python 3.13 plugin runtime audit reports no known vulnerabilities at review time. Dependency versions are unchanged from v0.2.0.
- Git-history secret scanning reports no matches. This is a detector result, not a guarantee that all possible secrets are absent.

Run the commands in [CONTRIBUTING](../CONTRIBUTING.md) and the live/audit commands in the [v0.2.0 record](release-v0.2.0.md) to reproduce the checks. Build the release with `uv run --frozen python scripts/package_release.py`. Verify the extracted archive and its SHA256SUMS before publishing. Consult the published release notes for the final CI and artifact results.

## Boundaries

The [v0.2.0 record](release-v0.2.0.md) documents the prior installation and visual checks. This patch does not change installation instructions or report layout. A complete model-driven narrative conversation in each client has not been retested. Public registry existence does not prove safety, and unavailable evidence remains a review limitation.
