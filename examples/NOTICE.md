# Attribution and data terms

OSS Gate's original code and original documentation are MIT licensed, copyright 2026 yesolz. The MIT grant does not relicense third-party data, package licenses, trademarks or source quotations.

## Public evidence

- **Google Open Source Insights (deps.dev)** supplies package metadata, dependency graphs and associations. Its generated data is [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); aggregated data retains its source terms. See the [API data and terms section](https://docs.deps.dev/api/v3/#data). Examples preserve the normalized 2026-11-17 snapshots. The bilingual narratives, formatting and policy reassessments are changes made by OSS Gate; the source JSON is unchanged.
- **OSV.dev and upstream advisory publishers** supply vulnerability records. OSV aggregates sources with different licenses; [check the source inventory](https://google.github.io/osv.dev/data/) before redistributing a new dataset. The 42 advisory entries included in this repository are GHSA records from the **GitHub Advisory Database**, available under [CC BY 4.0](https://github.com/github/advisory-database/blob/main/LICENSE.md), accessed through deps.dev and OSV. Individual IDs, aliases, source links and affected ranges remain in each snapshot. Narratives may be truncated by the historical tool; they are not a full advisory mirror.
- **OpenSSF Scorecard** supplies dated repository signals through deps.dev. Scores and reasons are attributed in each report; an unevaluated score is not a zero. See the [Scorecard project](https://github.com/ossf/scorecard).
- **Cognition DeepWiki** supplies AI-generated public-repository explanations. Examples identify these as generated material, preserve the saved source context where available, and distinguish missing evidence. See [DeepWiki MCP](https://docs.devin.ai/work-with-devin/deepwiki-mcp) and [Cognition's terms](https://cognition.com/legal/platform-terms-of-service). OSS Gate does not claim ownership of upstream repository code or grant rights to third-party quoted material.
- The reviewed projects and their contributors retain rights in their software: [FastAPI](https://github.com/fastapi/fastapi), [Requests](https://github.com/psf/requests), and [Next.js](https://github.com/vercel/next.js). Their licenses are evidence about those projects, not OSS Gate's own license.

Reports preserve identifiers and source text; translations and policy explanations are derivative presentation. Attribution does not imply endorsement by any provider. The static demo uses system fonts and includes no redistributed font files, third-party JavaScript bundles or tracking assets.

## Runtime dependencies

The plugin downloads dependencies through uv using the committed lockfile; their code is not vendored in the release archive. Direct dependencies are the Python MCP SDK (MIT), HTTPX (BSD-3-Clause), and markdown-it-py (MIT). Their own notices and transitive dependency licenses remain applicable. See the release audit inventory for exact installed versions and license metadata. Metadata screening is not a substitute for reviewing the applicable license texts when redistributing dependencies.
