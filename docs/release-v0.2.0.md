# v0.2.0 validation record

Local checks were performed on 2026-11-20 (Asia/Seoul). These observations describe the release candidate, not an independent certification. An archive or draft release is not a published release.

## Verified behavior

- 23 unittest methods pass, including the retained 177 API, graph, manifest and error-handling assertions.
- Python 3.10.18 and 3.13.5 pass locally on macOS. CI defines Ubuntu, macOS and Windows jobs; consult actual runs before claiming those platforms passed.
- All four skills pass the skill format validator. Claude Code validates the plugin and marketplace manifests.
- Claude Code 2.1.212 installs from a local marketplace, including an extracted release archive. Codex CLI 0.163.0-alpha.11 installs/enables the native local marketplace plugin. Test installations were removed afterward.
- The locked stdio server initializes through an MCP client, exposes six tools and returns structured validation errors.
- Live deps.dev, OSV and DeepWiki calls succeed. A Requests 2.25.1 collection preserves raw responses, verifies hashes and does not approve the known-vulnerable target.
- Four historical JSON snapshots retain their original SHA-256 hashes. Four package reviews, one periodic report and one proposal have Korean and English Markdown and HTML.
- The static build has 18 HTML pages including compatibility redirects. Local links, language pairs, absent input forms and absent remote runtime assets are checked.
- Aside inspection covers the Korean demo, English review, language navigation, responsive layout at 150% zoom and browser print preview. No mobile-device visual test is claimed.
- Ruff's configured correctness rules and Git whitespace checks pass. The release excludes virtual environments, private generated reviews and the retired AWS runtime.

## Deterministic logic and exceptions

The agent writes source-linked explanations. Shared Python functions classify licenses, combine advisory aliases, calculate verdicts, aggregate snapshots, verify integrity and render HTML. Both languages use the same calculation and evidence.

Regressions cover unknown license IDs, SPDX expressions/exceptions, version ranges, timeouts, failed queries, malformed/paginated OSV responses, missing/substituted graphs, invalid advisory IDs, missing severity, inconsistent counts, available fixes for vulnerable versions, transitive aliases, failed verification, missing translations, HTML injection, hash changes, path traversal, evidence overwrite attempts, distinct versions and missing portfolio inputs. A failed verification is retained in both individual and aggregate reports.

## Independent audits

`pip-audit` found no known vulnerabilities in the 31 locked runtime packages on Python 3.13, the 32 runtime packages on Python 3.10, or the 56-package Python 3.13 development environment tested on macOS. Results are in [runtime-vulnerabilities.json](audit/runtime-vulnerabilities.json) and [development-vulnerabilities.json](audit/development-vulnerabilities.json). The additional runtime result is [runtime-python310-vulnerabilities.json](audit/runtime-python310-vulnerabilities.json). These are time-specific registry matches, not source-code or reachability analysis. Platform-conditional dependencies require that platform's audit.

[runtime-licenses.json](audit/runtime-licenses.json) records versions, declared expressions/classifiers and license-file metadata. Declarations include MIT, MIT-0, BSD-3-Clause, Apache-2.0, PSF-2.0, an Apache/BSD alternative and certifi's MPL-2.0. Dependencies are downloaded unchanged by uv; their implementations are not vendored in the source archive. Their upstream licenses remain applicable. Missing license-file metadata is not proof of an absent license. Example data has separate attribution in [NOTICE](../NOTICE.md).

Gitleaks 8.30.1 checks Git history and the unpacked distribution with full redaction. A zero-match result means no detector matches, not proof that every possible secret is absent. See [secret-scan.json](audit/secret-scan.json) for scope and results.

A Python 3.10 development audit found 17 advisories in filelock 4.1.0, a dependency of the audit tooling. Patched filelock requires Python 3.11+. Development tooling now requires Python 3.11+ with an explicit patched constraint; the plugin runtime retains Python 3.10 support and has no filelock dependency. See [remediations.json](audit/remediations.json).

## Reproduce

Run the checks in [CONTRIBUTING](../CONTRIBUTING.md), then:

```sh
uv run --frozen python scripts/smoke_mcp.py --live
uv export --project plugins/oss-gate --frozen --no-dev --no-emit-project --output-file /tmp/oss-gate-runtime.txt
uv run --frozen pip-audit --requirement /tmp/oss-gate-runtime.txt --no-deps --disable-pip
uv run --frozen pip-audit
uv run --frozen python scripts/package_release.py
gitleaks git . --redact=100
```

Extract the archive into a new directory, repeat the offline/MCP checks there and run `gitleaks dir` on it. Compare downloads against SHA256SUMS. ZIP entry timestamps are fixed for reproducibility, not evidence of creation or publication. Use GitHub's actual `published_at` after publication, not commit dates or draft creation time.

## Boundaries and publication

Client installation and actual MCP protocol behavior were tested separately. A complete model-driven conversation producing a fresh narrative in each client has not been exercised. Narrative quality and invocation depend on the host/model.

The public repository begins with the standalone release and does not include the historical workshop deployment source or its Git history. No AWS resources were deleted. Local checks do not establish a live Pages deployment; the published release notes record the actual hosted CI, deployment and publication results.
