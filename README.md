# OSS Gate

**An open-source adoption review you can understand, generated in your own agent.**

[한국어](README.ko.md) · [Live demo](https://yesolz.github.io/oss-gate/) · [Example review](examples/reviews/psf-requests-2.34.2/review.en.md) · [Installation](docs/installation.md) · [How decisions work](docs/policy.md)

Give OSS Gate a public repository or package. It combines license and dependency metadata, known vulnerabilities, maintenance signals and a sourced explanation of the software into a readable adoption review. Keep the Markdown, open the offline HTML, and inspect the evidence JSON behind the verdict.

Your agent supplies the reasoning and writing. Two MCP connections supply context: **DeepWiki** for repository explanations, and the bundled **depsdev** server for **deps.dev + OSV**. The latter runs locally. You do not need to operate a server or buy a separate model API key for OSS Gate. Your agent plan, local execution permissions and upstream service limits still apply.

## Install

Use a recent Claude Code or Codex client with plugin and local MCP support, plus [uv](https://docs.astral.sh/uv/getting-started/installation/). Python 3.10+ is required; uv can provision it. Ordinary web-only chat sessions cannot run the bundled local server.

Claude Code:

```sh
claude plugin marketplace add yesolz/oss-gate
claude plugin install oss-gate@oss-gate
```

Codex versions with the plugin CLI:

```sh
codex plugin marketplace add yesolz/oss-gate
codex plugin add oss-gate@oss-gate
```

Restart the agent session after installation. If your Codex version does not have `plugin add`, use its local marketplace installation UI or the [manual MCP and skill setup](docs/installation.md#manual-codex-setup). Distribution through this repository does not imply listing in a public plugin store.

## Use

In Claude Code:

```text
/oss-gate:oss-review pypi requests 2.25.1 --language en
/oss-gate:oss-review https://github.com/fastapi/fastapi --language ko
/oss-gate:oss-review npm next 15.1.0 --language both
```

In Codex, invoke the installed `oss-review` skill, for example:

```text
Use oss-review to review pypi requests 2.25.1 in English.
```

Choose **Korean**, **English**, or **both**. Without a choice, the request language is used. Both languages share one evidence snapshot and verdict. Asking for a translation later reuses the snapshot; asking to refresh creates a new one.

A review produces:

```text
reviews/<package-version>/<timestamp-id>/
  data.json                 # normalized evidence and deterministic verdict
  api-responses.json        # original public API JSON
  evidence-sha256.json      # integrity hashes
  deepwiki.json             # sourced explanation, with capture limitations
  verification.json         # agent evidence check
  review.en.md              # selected language(s) only
  report.en.html
  review.ko.md
  report.ko.html
```

HTML works offline, includes detailed findings and source data, and can be printed to PDF from the browser. No review is sent to an OSS Gate backend. You can also use `oss-viz`, `periodic-report`, and `proposal-draft` for existing results. [Usage guide](docs/usage.md)

## What it adds

OSS Gate helps answer: what does this software do, what needs review before adoption, and which evidence supports that decision? It keeps versions, limitations, suggested actions and source references together in a report you can discuss with a teammate.

OSV Scanner and OSS Gate can use the same vulnerability data while serving different workflows. Sharing OSV data does not establish equivalent scanning coverage: lockfile parsing, supported ecosystems, dependency resolution and analysis capabilities differ. OSS Gate is an agent-assisted review workflow, not a replacement for a dedicated scanner, a legal opinion, or an enterprise SCA program. [Scope and policy](docs/policy.md)

## Examples and demo

Four historical package reviews, a periodic report and an adoption proposal are available in **both languages** under [examples](examples/README.md). They use saved 2026-11-17 data, not live results. Important corrections are visible: a prior-version graph cannot approve FastAPI's requested version, a fixed release does not clear a vulnerable older release, and a missing Flask snapshot is excluded from portfolio totals.

The web is a **read-only static demo**. It has no package input, account, API route or model call. Build it with `uv run --frozen python scripts/build_site.py`; serve `site/generated` with any static server. The public demo is hosted on [GitHub Pages](https://yesolz.github.io/oss-gate/); the included workflow also supports your own deployment. [Deployment and prototype retirement](docs/deployment.md)

## Develop and verify

Development and audit tools need Python 3.11+; the installed plugin supports Python 3.10+.

```sh
git clone https://github.com/yesolz/oss-gate.git
cd oss-gate
uv sync --frozen
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen python scripts/smoke_mcp.py          # local protocol only
uv run --frozen python scripts/smoke_mcp.py --live   # public API connections
uv run --frozen python scripts/build_examples.py
uv run --frozen python scripts/build_site.py
```

[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Changelog](CHANGELOG.md) · [MIT license](LICENSE) · [Third-party attribution](NOTICE.md)

[Release validation](docs/release-v0.2.3.md)
