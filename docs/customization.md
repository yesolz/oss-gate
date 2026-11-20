# Optional policies and CLI

[한국어](customization.ko.md)

Ordinary OSS Gate reviews need no configuration. Keep using the plugin and natural-language requests. Optional settings apply only when explicitly selected, and additional-policy report sections appear only for those reviews.

For CLI commands, configuration fields, evidence requirements and security boundaries, see the bundled [execution reference](../plugins/oss-gate/skills/oss-review/references/execution.md). Examples are [settings](../plugins/oss-gate/policies/example.json) and [communication evidence](../plugins/oss-gate/policies/communication.example.json). They are illustrative and are never loaded automatically.

Choose a policy with an absolute `OSS_GATE_POLICY` path in each local MCP server's environment, or with `cli.py --policy /absolute/settings.json <command>`. For an installed plugin, configure both `depsdev` and `deepwiki` through the host's MCP environment settings. Restart after changing that environment. A manual server entry can include:

```json
{"env": {"OSS_GATE_POLICY": "/absolute/settings.json"}}
```

This is a fragment to add to the existing local server definition, not a complete host configuration. Do not configure one adapter and assume the other inherits it. No policy is discovered inside the repository being reviewed. Keep policy files outside untrusted projects and use host controls to protect them when enforcement matters.

The CLI supports `project`, `audit`, `plan`, `collect`, `explain` and `render`. It shares the same collection and policy code as MCP. It does not itself write an AI narrative: the user's agent reads the saved evidence and writes Markdown, then renders HTML. `explain` accesses the same external DeepWiki service through fixed topic questions. CLI mode does not make network operations offline or remove the user's model provider from the data flow. Token savings depend on the host's tool discovery and output reading; no measured reduction is claimed.

A new policy can add release-waiting or external-communication conditions without erasing the default screening findings. Reported communication facts are explicitly supplied reviewer evidence, not automatically verified telemetry detection. The saved evaluation clock and policy hash make repeated rendering stable. Existing evidence and report files are not migrated or changed automatically.

## Repository hosts and npm mirrors

Set `network.allowed_repository_hosts` to exact hostnames such as `["github.com"]` to restrict repository identities sent to external services. Omission preserves existing behavior; `[]` blocks all repository-bearing requests. Hostnames normalize case, trailing dots and IDNA. Wildcards, ports and URLs are not allowed in this list. This is separate from the API destination allowlist. Identifier denies still win: `repo:company/*` refers to GitHub, while `repo:*.example.internal/*` covers enterprise subdomains. Discovered repositories receive the same checks. Allowing a host does not make DeepWiki support it.

Set `network.npm_registry_url` to an HTTPS npm-compatible base URL to use a mirror for existence checks after a deps.dev 404. Base paths and explicit ports are supported. The `npm` service and identifier restrictions still apply. The [mirror example](../plugins/oss-gate/policies/npm-mirror.example.json) is illustrative and never loaded automatically.

No public npm fallback or redirect is followed. Mirror misses are reported as `mirror_package_not_found` or `mirror_version_not_found`, not public nonexistence. A mirror hit is only an existence diagnostic, not vulnerability evidence or a byte-identity check. Authentication errors remain unverified. This release does not load credentials or `.npmrc`, bypass TLS, support PyPI mirrors, or replace deps.dev/OSV in a disconnected network.

For an installation that registers no MCP servers, choose `oss-gate-cli` in the [installation guide](installation.md). The analysis code, policies and report templates are generated from the same maintained source as the standard plugin.
