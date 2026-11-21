# v0.4.1 validation record

This patch fixes false PyPI version mismatches discovered while reviewing OSS Gate's own dependencies. For example, deps.dev may return `5.0.0` for a request for `5.0`. The shared comparison now uses PEP 440 through pinned `packaging==26.3`, preserving the requested version and distinguishing prereleases, postreleases, development releases, epochs and local versions. Other ecosystems retain strict version comparison.

Metadata lookup, registry existence checks, dependency license evidence, publication timelines and review policy use the same identity rules. Python requirements audits also accept valid exact PEP 440 versions without accepting ranges or wildcards. Responses identifying another package or release cannot supply license evidence.

API and DeepWiki HTTP bodies are capped at 16 MiB before parsing. Requests ask for identity encoding and reject unexpected compression. Streaming bodies have elapsed-time checks in addition to socket timeouts; a DeepWiki operation is cancelled after 120 seconds. Rejected or incomplete responses do not become clean vulnerability results or proof of package absence. See [SECURITY.md](../SECURITY.md) for scope and remaining limits.

The CLI distribution check also permits excluded local virtual-environment symlinks while continuing to reject symlinks in distributed product files.

## Validation

On 2026-11-21, local Python 3.10 and 3.13 each passed 83 unittest tests, including the seven real normalization failures, wrong-release rejection, response-size and elapsed-time limits, stream cleanup, policy enforcement, hostile HTML and evidence integrity. Ruff, both MCP adapters, standalone CLI execution, bilingual examples, 18 static pages and distribution checks passed. The required GitHub Actions matrix covers Ubuntu 3.10/3.13, macOS 3.13 and Windows 3.13 before merging.

Self-review combined the development and runtime locks across platform/Python markers: 58 package names and 64 distinct package/version pairs. All 64 metadata lookups succeeded; the seven previous normalization failures were resolved. OSS Gate's OSV audit returned zero known vulnerabilities, zero skipped entries and no incomplete queries. A pip-audit cross-check of the local macOS Python 3.13 environment returned zero known vulnerabilities for 56 development packages and 32 runtime packages. This is not a claim that every platform installs all 64 pairs or that zero known findings proves safety.

All six direct dependencies were collected again with preserved API responses and evidence hashes. Automatic outcomes were retained: packaging allowed; MCP and Ruff conditional; pip-audit, HTTPX and markdown-it-py held. License metadata remains unknown for pip-audit, defusedxml and pywin32; certifi declares MPL-2.0. Ruff's dependency graph is unavailable. HTTPX and markdown-it-py's maintenance holds derive from a 2026-08-24 Scorecard and do not establish present abandonment. No verdict threshold was relaxed to pass this self-review.

DeepWiki returned an unindexed-repository response for OSS Gate itself. The connection worked, but no repository explanation was obtained. Local self-review HTML was inspected in Aside. Gitleaks found no known secret patterns in the then-current 22-commit history or distributable working files. Private local validation outputs are excluded from the release archive.

These checks are a maintainer's regression and dependency review, not an independent penetration test, legal approval or security certification.
