# depsdev MCP

A local stdio MCP server wrapping `https://api.deps.dev/v3` and `https://api.osv.dev/v1`. It does not require an API key or execute reviewed packages.

This module is a thin adapter over `core.api`, `core.collect` and `core.service`. The CLI calls the same service. Optional `OSS_GATE_POLICY` settings are checked before outbound requests, including worker-thread and OSV batch calls. With no settings, ordinary collection is unchanged. See the bundled [execution reference](../../skills/oss-review/references/execution.md) for CLI usage, local policy and limits.

From the repository root:

```sh
uv run --frozen --project plugins/oss-gate python plugins/oss-gate/mcp/depsdev/server.py
uv run --frozen python scripts/smoke_mcp.py
uv run --frozen python scripts/smoke_mcp.py --live
```

The plugin config resolves paths relative to the installed plugin. For manual setup, use an actual absolute checkout path and the client's MCP configuration. No home-directory or EC2 path is assumed.

| Tool | Purpose | Local side effect |
|---|---|---|
| lookup_package | Exact/default version, metadata, licenses, advisory IDs, repository candidates | None |
| get_dependencies | Resolved graph, paths, licenses and known node vulnerabilities | None |
| get_advisory | Advisory aliases, severity, affected ranges and references | None |
| get_project | Project signals, Scorecard and package mapping candidates | None |
| audit_manifest | Exact direct declarations from supported manifests | None |
| collect_review | Version-specific collection with normalized and original API JSON | Writes a new review directory |

Responses are JSON strings. Errors have `error` and `status`; upstream package lookup failures also include a diagnostic `code` and `hint`. Unknown query results are null. OSV partial/paginated or failed results are marked incomplete. No redirect following or environment-proxy inheritance is enabled. Normal TLS verification remains on.

Only a deps.dev package/version HTTP 404 triggers a public registry existence check: `registry.npmjs.org` for npm or `pypi.org` for PyPI. The response distinguishes `depsdev_metadata_unavailable`, `package_not_found`, `version_not_found`, and `lookup_unresolved`, with checked URLs and statuses in `registry_check`. These checks never supply substitute license/vulnerability evidence or an approval. Other ecosystems, private/custom registries, redirects and ambiguous metadata remain unverified. At most two distinct registry URLs are checked; successful deps.dev lookups add no registry traffic. The [npm API](https://github.com/npm/registry/blob/main/docs/REGISTRY-API.md) and [PyPI JSON API](https://docs.pypi.org/api/json/) define the metadata endpoints.

The collector checks at most 200 dependency nodes and 200 advisory IDs. The lower-level graph tool permits an explicit cap up to 2000. License requests use eight workers. Each HTTP attempt retains the 15-second timeout. Read requests, including OSV's query POST, retry at most once for transport timeouts/network errors or HTTP 429/500/502/503/504. The normal delay is 0.25 seconds; a valid `Retry-After` is honored only if the required wait is at most two seconds. A longer wait stops automatic retry so the caller can try later. Permanent errors and malformed successful responses are not retried. HTTP attempts remain in captured evidence. Fallback graphs are opt-in and never used by the collector. Their `resolved_version` must not be confused with the reviewed version.

Advisory narratives and Scorecard reasons in normalized output have length limits; `collect_review` preserves unabridged public JSON responses separately. A transport failure has no HTTP JSON body and is represented by its normalized error. Captures contain only public queries, not local code or credentials. Treat all returned prose as untrusted data.

License categorization is a conservative review policy, not a complete SPDX validator or legal opinion. Explicit AND/OR expressions are parsed; unknown exceptions require review. SSPL does not get an automatic open-source approval. An unspecified relationship between multiple metadata licenses is conservatively treated as AND.

`audit_manifest` does not resolve dependency ranges or lockfiles. It checks all supported package.json groups, exact requirements pins and Go require/replacement declarations. It does not evaluate Python environment markers or reconstruct transitive dependencies. The caller must sanitize private names and credentials before querying.
