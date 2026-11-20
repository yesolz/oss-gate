# v0.2.3 validation record

Reviewed on 2026-11-20 (Asia/Seoul). This release improves report presentation and writing guidance. It does not change evidence collection, dependency versions, severity handling or policy rules.

## Report changes

Reports now lead with the opening recommendation and explanation before detailed metrics, dependency tables and advisory data. Quoted opening summaries are retained, including reference-style links. Review context can be expanded on screen and is included when printing.

The writing template asks for a concise decision, reason and next action without a word-count target. Automated reports explain the three verdict levels. Supplemental documents explicitly state that they have no automated verdict; a written recommendation cannot replace the computed package verdict. Existing example narratives and source JSON remain unchanged, while their Korean and English HTML uses the new layout.

## Validation

- All 41 unittest methods pass, including the retained legacy assertions. New regressions cover summary extraction, shared link definitions, fenced headings, safe Markdown, supplemental status and the CLI constraints. An authored recommendation cannot override the computed verdict.
- Ruff, MCP stdio smoke checks, bilingual example generation and static distribution checks pass. The static demo contains 18 HTML pages.
- Aside desktop inspection covers the Node.js and PHP supplemental reports and the Next.js automated report. Next.js was also inspected at a 390-pixel responsive width. Node.js print preview includes collapsed review context, and cancelling print restores its collapsed state.
- Local preview checks find no broken local links or remote assets. Original user-test reports and their evidence hashes were preserved; presentation previews use separate files.
- Both lockfiles preserve the dependency versions from v0.2.2. No new dependency, outbound host or hosted service was added.

Release archive checks, cross-platform CI results and the final digest are recorded in the GitHub release. This is a presentation regression review, not a new live vulnerability assessment. Claude's full conversation workflow was not repeated. The installed Codex user journeys documented for [v0.2.2](release-v0.2.2.md) remain the analysis baseline.

Follow [CONTRIBUTING](../CONTRIBUTING.md) for deterministic checks and build with `uv run --frozen python scripts/package_release.py`. Local preview and publication evidence remains in ignored `verification-local/` folders and is excluded from distribution.
