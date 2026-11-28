# v0.6.0 validation record

Prepared on 2026-11-28 (Asia/Seoul). This release adds local multi-ecosystem repository dependency reviews through CLI and MCP, alongside the existing single-package workflow.

## Changes and compatibility

- Discover and hash supported files without cloning, installing dependencies or executing target project code. Query identified public package/version tuples once and retain their project occurrences.
- Analyze Yarn Berry workspace locks, Go module/workspace declarations, Cargo locks/workspaces, Java/Kotlin Maven resolved JSON trees and Gradle dependency locks, plus Swift Package.resolved schemas 1/2/3. Report declared, locked and resolved version bases explicitly.
- Import native Trivy schema 2 and Grype image JSON offline. Associate Dockerfile/Compose declarations only with matching canonical repository names and SHA-256 manifest digests. Retain suppressed findings, component license policy and input provenance; count container findings separately from online package queries.
- Generate Korean/English Markdown and offline HTML from sealed repository evidence. Preserve input hashes, public API responses, policy restrictions, collection caps and unsupported-resolution gaps.
- Add pinned PyYAML 6.0.3 and Tomli 2.5.0 parsers with bounded data traversal. Existing service/identifier/TLS policies remain in force; no new outbound service or scanner executable is required. The installed plugin supports Python 3.10+, while development/audit tools require Python 3.11+.

Repository evidence uses `oss-gate.repository-review/1` and `oss-gate.repository-policy/1`, separate from the package policy/3 workflow. Existing package portfolio/reassessment commands do not accept repository snapshots. Use `repo-plan`, `repo-collect` and `repo-render`, or MCP planning/collection followed by CLI rendering. See the [English](usage.md) and [Korean](usage.ko.md) usage guides for required filenames and export examples.

## Material limits

Go requirements do not establish the selected build list. Gradle locks and Swift pins do not establish direct/transitive relationships. Maven exports do not prove current profiles, repositories or build configuration. Swift license metadata is unavailable in this adapter and unknown licenses retain hold; advisory records under ambiguous noncanonical names may not match. Unsupported/custom/local sources remain explicit gaps.

Container support imports supplied scan results; it does not pull, build, run or scan images. A tag or image configuration ID cannot substitute for a manifest digest. Base-image results do not establish final-build coverage. Unknown severity, zero imported findings and scanner filters/database freshness cannot establish allow. Raw scanner environment/configuration is excluded; retain original scanner reports independently if required for audit. Docker Hub/Scout is not queried.

## Validation

The feature candidate passed 177 unit tests on Python 3.10.18 and 3.13.5, a 637-case malformed-input mutation check, live Maven/Swift API collection, native upstream Swift/Trivy/Grype format checks, CLI generation parity, both MCP adapters, example/static-site generation, distribution links, dependency audits and a redacted secret scan of an extracted candidate archive. The feature commit also passed the Ubuntu 3.10/3.13, macOS 3.13 and Windows 3.13 GitHub Actions matrix. Exact saved-run scope and compatibility fixes are documented in the [repository development record](repository-review-development.md).

The versioned candidate passed 180 tests, including three new seal/navigation/escaping regressions, on Python 3.13.5 and 3.10.18, Ruff, canonical/generated CLI parity, both MCP adapters, example/static-site generation and 20-page distribution/link checks. A cache-free frozen Python 3.10 installation of the extracted v0.6.0 ZIP installed 35 runtime distributions. The extracted tests, explicitly isolated Python 3.10 MCP subprocesses, offline container CLI collection and both Claude Code plugin manifests passed. Fresh runtime/development dependency audits found no known vulnerabilities, and the extracted archive passed a redacted Gitleaks scan. These are scoped checks, not an independent security audit.

The user reported that both languages of the initial release candidate were readable and language switching worked. The renderer shares the existing theme, fonts, colors, side panel, table styles, language switching and print support. After the user requested visual consistency, repository reports also reuse the package report's verdict seal and interpretation guide and add a contents menu with links to actual generated sections. Per-project tables remain, and the report does not invent package-only maintenance or dependency-area verdicts. Automated checks verify each contents link has a unique destination, the shared seal matches the saved verdict, and rendering preserves the sealed evidence. The assistant cannot independently inspect browser pixels in this session because browser control is unavailable. Mobile/print visual checks and independent first-user testing remain unverified.
