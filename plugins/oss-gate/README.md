# OSS Gate plugin

Shared skills, local MCP and report rendering for Claude Code and Codex.

- Claude manifest: `.claude-plugin/plugin.json`; MCP: `.mcp.json`.
- Portable Codex manifest: `plugin.json`; MCP: `mcp.json`.
- Both hosts use the same `skills/`, `core/`, MCP implementation and locked runtime.
- No hosted review backend, API key, global hook or reviewed-package execution.

See the [repository installation guide](https://github.com/yesolz/oss-gate/blob/main/docs/installation.md) or its [Korean version](https://github.com/yesolz/oss-gate/blob/main/docs/installation.ko.md).

From a checkout, start the server with:

```sh
uv run --frozen --project plugins/oss-gate python plugins/oss-gate/mcp/depsdev/server.py
```

The `collect_review` MCP tool writes unique local evidence files to the output root explicitly supplied by the agent. Other MCP tools query public metadata without local writes. Reports use the user-selected language and preserve uncertainty. See `skills/oss-review/references/workflow.md` for the workflow and the root NOTICE for third-party data terms.
