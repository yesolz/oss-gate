# v0.4.0 validation record

Reviewed on 2026-11-20 (Asia/Seoul). This release adds an optional CLI-only plugin and explicit network configuration without requiring a policy for ordinary use.

## Changes and migration

The existing `oss-gate` plugin remains available with its two MCP adapters. The new `oss-gate-cli` plugin includes the same four skills and shared analysis functions, with no MCP server registrations. Both distributions are generated from one maintained implementation. Choose one plugin; installing the CLI variant does not remove an existing MCP installation. See the [installation guide](installation.md).

The CLI adds `project` and `audit` commands. Agents still interpret saved evidence and write the narrative. No separate model API key or hosted OSS Gate service is added.

Optional `network.allowed_repository_hosts` restricts repository identities before outbound calls, including repositories discovered in package metadata. Omission preserves the default behavior; an empty list blocks repository-bearing requests. Existing GitHub patterns continue to work, and host-qualified patterns support internal repository names. DeepWiki explicitly rejects unsupported repository hosts instead of treating them as GitHub repositories.

Optional `network.npm_registry_url` selects an HTTPS npm metadata mirror for existence checks after a deps.dev not-found response. Mirror absence is reported as mirror-specific, not proof of absence from public npm. Errors stay unverified, and there is no public-registry fallback, automatic credential loading, redirect following or TLS bypass. This does not replace deps.dev or OSV analysis. See [customization](customization.md).

## Validation

- All 70 unittest methods pass on Python 3.10 and 3.13. New cases cover repository identity normalization, host restrictions, generated distribution drift, standalone CLI execution and mirror response/error boundaries.
- Ruff, generated-plugin consistency, MCP stdio smoke checks, bilingual example generation and static distribution checks pass. The demo contains 18 HTML pages. Example source evidence and narratives remain unchanged; regenerated HTML updates the generator version.
- A temporary local marketplace installation was tested in Claude Code 2.1.212 and Codex 0.163.0-alpha.11. The CLI plugin contains four skills and no MCP configuration or server directory. Temporary test installations were removed after validation.
- The installed Codex CLI distribution collected live npm metadata and OSV evidence for `is-number@7.0.0`, saved a DeepWiki overview, and rendered Korean and English reports outside the plugin directory. Live checks also exercise the existing MCP adapters, a vulnerable package pin, evidence hashes and selected-policy blocking.
- Mirror tests use controlled HTTP responses for success, package/version absence, authentication failures, server failures, redirects, timeouts and malformed or mismatched metadata. They cover scoped names, version build metadata, base-path boundaries and the absence of public fallback.
- Runtime dependency versions remain unchanged. The final dependency audit, cross-platform CI, archive inspection and ZIP digest are recorded in the GitHub release.

## Boundaries

No real corporate mirror or authenticated registry was available for testing. Registry credentials, PyPI mirrors and fully disconnected operation are outside this release. Policy restrictions govern OSS Gate requests, not other agent tools, dependency installation or users who can edit policy/code. See [security](../SECURITY.md).

No measured token reduction is claimed. This release tests actual plugin installation and installed CLI execution, not a new full natural-language conversation in each host. Report layout is unchanged; no new visual browser review was performed.

Local validation and publication records live under ignored `verification-local/` directories and are excluded from distribution. Follow [CONTRIBUTING](../CONTRIBUTING.md) to reproduce deterministic checks.
