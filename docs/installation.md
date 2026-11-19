# Installation

[한국어](installation.ko.md)

## Requirements

Use Claude Code or a local Codex client that supports plugins, skills and MCP. Authenticate the client with your own supported account/plan. OSS Gate itself does not require a model API key. Web-only chat, local execution restrictions, organization policies and plan-specific limits can prevent use even when you have a subscription.

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Git. The runtime needs Python 3.10+; uv can install a compatible interpreter. The first run downloads pinned Python dependencies. Subsequent runs use the local cache. No Node.js, AWS account, jq or dedicated server is required for OSS Gate.

## Claude Code

```sh
claude plugin marketplace add yesolz/oss-gate
claude plugin install oss-gate@oss-gate
```

For a checkout before publication:

```sh
git clone https://github.com/yesolz/oss-gate.git
cd oss-gate
claude plugin marketplace add .
claude plugin install oss-gate@oss-gate
```

Alternatively load the checkout for one session with `claude --plugin-dir ./plugins/oss-gate`. Restart after installation, inspect `/mcp`, and confirm both `deepwiki` and `depsdev` connect. Invoke `/oss-gate:oss-review`.

Uninstall using `claude plugin uninstall oss-gate@oss-gate`, then `claude plugin marketplace remove oss-gate` if no longer needed. This does not delete reviews you generated.

## Codex

On a client with the plugin CLI:

```sh
codex plugin marketplace add yesolz/oss-gate
codex plugin add oss-gate@oss-gate
codex plugin list --marketplace oss-gate
```

For a checkout, replace `yesolz/oss-gate` with its absolute path or `.` from the repository root. The catalog is `.agents/plugins/marketplace.json`. The package uses portable `plugin.json` and `mcp.json`. If installation is exposed only in your client's Plugins UI, add the repository marketplace and install OSS Gate there.

Start a new local session, confirm both MCP connections, then request the `oss-review` skill. Exact invocation and plugin UI availability vary with client version. The release validation record names versions actually tested.

Remove with `codex plugin remove oss-gate@oss-gate`, then `codex plugin marketplace remove oss-gate` if desired. Generated reports remain in your workspace.

## Manual Codex setup

For clients without plugin installation, keep a local checkout. Register the MCPs using absolute paths:

```sh
codex mcp add oss-gate-deepwiki --url https://mcp.deepwiki.com/mcp
codex mcp add oss-gate-depsdev -- uv run --frozen --project /absolute/path/oss-gate/plugins/oss-gate python /absolute/path/oss-gate/plugins/oss-gate/mcp/depsdev/server.py
```

Replace `/absolute/path/oss-gate` with the actual checkout location. Add symlinks for the four skill directories to your supported skills location, for example `~/.agents/skills/oss-review` pointing to `<checkout>/plugins/oss-gate/skills/oss-review`. Do not overwrite an existing skill with the same name; choose an isolated workspace or use the plugin path instead. Keeping links to the original directories preserves shared references and renderer paths. On systems without symlink support, copy the entire plugin and link/configure from that stable location; copying only SKILL.md is insufficient.

Remove only the links and MCP entries you added (`codex mcp remove oss-gate-deepwiki`, `codex mcp remove oss-gate-depsdev`). Do not delete unrelated client configuration.

## Connection and privacy checks

- depsdev contacts `api.deps.dev` and `api.osv.dev` with public package names/versions, repository identifiers and selected manifest package entries.
- DeepWiki receives the public repository name and your research questions. Your model provider receives the conversation/tool context under that client's terms.
- The collector writes to the output folder chosen by the agent. Prefer an absolute workspace path so the client's server working directory cannot change where results go.
- The MCP does not execute reviewed packages. The agent and uv still run local code; normal host permissions apply. The plugin does not install a global network-blocking hook.
- Do not send private package names, credentials or private repository content. Inspect manifests before querying them.

`uv: command not found` means the desktop client's PATH does not include uv. Restart the app after installation or configure the MCP command to uv's actual absolute path. A missing graph or unindexed wiki is a coverage limitation, not an installation failure. Rate limits/timeouts remain unknown evidence; try a new review later instead of replacing them with zeros.

Official host references: [Claude marketplaces](https://code.claude.com/docs/en/plugin-marketplaces), [OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins), [Codex MCP](https://developers.openai.com/codex/mcp).
