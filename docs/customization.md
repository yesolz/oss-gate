# Optional policies and CLI

[한국어](customization.ko.md)

Ordinary OSS Gate reviews need no configuration. Keep using the plugin and natural-language requests. Optional settings apply only when explicitly selected, and additional-policy report sections appear only for those reviews.

For CLI commands, configuration fields, evidence requirements and security boundaries, see the bundled [execution reference](../plugins/oss-gate/skills/oss-review/references/execution.md). Examples are [settings](../plugins/oss-gate/policies/example.json) and [communication evidence](../plugins/oss-gate/policies/communication.example.json). They are illustrative and are never loaded automatically.

Choose a policy with an absolute `OSS_GATE_POLICY` path in each local MCP server's environment, or with `cli.py --policy /absolute/settings.json <command>`. For an installed plugin, configure both `depsdev` and `deepwiki` through the host's MCP environment settings. Restart after changing that environment. A manual server entry can include:

```json
{"env": {"OSS_GATE_POLICY": "/absolute/settings.json"}}
```

This is a fragment to add to the existing local server definition, not a complete host configuration. Do not configure one adapter and assume the other inherits it. No policy is discovered inside the repository being reviewed. Keep policy files outside untrusted projects and use host controls to protect them when enforcement matters.

The CLI supports `plan`, `collect`, `explain` and `render`. It shares the same collection and policy code as MCP. It does not itself write an AI narrative: the user's agent reads the saved evidence and writes Markdown, then renders HTML. `explain` accesses the same external DeepWiki service through fixed topic questions. CLI mode does not make network operations offline or remove the user's model provider from the data flow. Token savings depend on the host's tool discovery and output reading; no measured reduction is claimed.

A new policy can add release-waiting or external-communication conditions without erasing the default screening findings. Reported communication facts are explicitly supplied reviewer evidence, not automatically verified telemetry detection. The saved evaluation clock and policy hash make repeated rendering stable. Existing evidence and report files are not migrated or changed automatically.
