# v0.3.0 validation record

Reviewed on 2026-11-20 (Asia/Seoul). This release adds optional customization and a local CLI while preserving the default screening rules. No policy file is required for ordinary plugin use.

## Changes and migration

MCP and CLI now share collection and policy functions. The CLI provides `plan`, `collect`, `explain` and `render`; the user's agent still writes the narrative from saved evidence. No separate model API key or hosted OSS Gate service is added.

An explicitly selected policy can restrict outbound services and package/repository identifiers before requests are sent, including dependency queries. It can add release-waiting and communication-review conditions. Saved policy content, its hash and a fixed evaluation time travel with sealed evidence. Additional rules cannot lower the default verdict. Reports show the additional policy only when selected, and portfolios reject mixed-policy comparisons.

DeepWiki now uses a local stdio adapter that connects on demand and sends public repository identifiers with fixed topic questions. Update the plugin and restart its MCP servers. Users with manually registered remote DeepWiki connections must replace them with the local adapter described in the [installation guide](installation.md). Configure `OSS_GATE_POLICY` separately for both adapters when restrictions are wanted. Existing review files are not migrated automatically.

## Validation

- All 56 unittest methods pass on Python 3.10 and 3.13. Extension regressions cover blocked requests before transport, malformed settings, transitive identifiers, environment-policy precedence, release-time boundaries, incomplete communication evidence, monotonic verdicts, saved-context reproducibility and mixed-policy portfolios.
- Ruff, MCP stdio smoke checks, bilingual example generation and static distribution checks pass. The demo contains 18 HTML pages. Existing example source evidence and narratives remain unchanged; regenerated HTML carries the new generator version.
- Live checks exercise deps.dev collection, an OSV vulnerable pin, preserved evidence hashes and the local DeepWiki adapter. Both MCP servers were also launched with all outbound services blocked. An actual CLI DeepWiki overview saved a nonempty response through the current upstream `ask_wiki_question` tool.
- Aside inspection covers default and selected-policy reports, Korean and English content, and a 390-pixel responsive layout. Synthetic policy previews are local validation fixtures, not real adoption decisions.
- Runtime dependency versions remain unchanged. Release archive inspection, a fresh dependency audit, cross-platform CI and the final ZIP digest are recorded in the GitHub release.

## Boundaries

Communication observations are reviewer-supplied evidence, not an automatic traffic scan or independent proof of reviewer identity. Missing or incomplete evidence remains uncertain. Policy restrictions govern OSS Gate requests; they do not control other tools, the model provider, dependency installation or a user who can change the code and policy files. See [customization](customization.md) and [security](../SECURITY.md).

No measured token reduction is claimed. Full Claude and Codex conversational journeys were not repeated for this release; the checks above exercise the adapters, CLI and shared functions directly. The installed Codex journeys in [v0.2.2](release-v0.2.2.md) remain the conversational baseline.

Local validation and publication records live under ignored `verification-local/` directories and are excluded from distribution. Follow [CONTRIBUTING](../CONTRIBUTING.md) to reproduce deterministic checks.
