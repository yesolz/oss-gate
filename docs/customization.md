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

## Additional CA certificates

If your network re-signs HTTPS certificates with a company CA, explicitly add its public certificates to the existing certifi trust bundle:

```json
{
  "schema": "oss-gate.settings/1",
  "name": "Company CA",
  "version": "1",
  "network": {"additional_ca_file": "/absolute/path/company-ca.pem"}
}
```

Use an absolute path on the machine running OSS Gate (Windows JSON example: `"C:\\Company\\company-ca.pem"`). The PEM file must contain public certificates only, no private keys, and be at most 1 MiB. Obtain it from your organization's trusted administrator. Omission preserves default trust. OS trust-store selection is not implemented; export the required public CA certificates to PEM instead.

The selected CA applies to OSS Gate's deps.dev, OSV, registry/mirror and DeepWiki requests. TLS chain, hostname and expiry verification remain enabled. Requests still enforce service/identifier policy, disable redirects and ignore ambient proxy and CA-path variables (`trust_env=False`). This setting does not configure a proxy URL, client authentication, your agent's other tools or uv's initial dependency download.

Each operation loads the file once and uses an isolated connection pool; dependency workers share only that operation's pool. An unreadable, malformed or oversized file returns `tls_configuration_invalid` before an HTTP request, with no fallback. `plan` validates the setting's shape without opening the file, so it does not establish certificate readiness. `collect` preserves the actual CA-file SHA-256 and certifi version in sealed `data.json#/tls_trust`; offline evaluation/rendering does not need the original file. A different CA file on the next operation is a new trust configuration, even if its path is unchanged.

Additional trust authorizes certificates issued by that CA for otherwise allowed destinations. A TLS-inspecting proxy can read those requests, so existing private-name restrictions remain necessary. The saved policy contains the local CA path; review that path before sharing reports. No certificate contents or private keys are stored in the report.

## License review settings

No settings are required for ordinary reviews. Configure exact SPDX IDs when you need additional restrictions:

```json
{"schema":"oss-gate.settings/1","name":"My review rules","version":"1",
 "review":{"license_restrictions":{"MPL-2.0":"hold","CC-BY-4.0":"conditional"}}}
```

Only `conditional` and `hold` are accepted. An alternative permitted OR branch remains available; the selected branch is recorded. Identifiers and license expressions are not rewritten.

For an attributed acceptance record, copy the exact `finding_sha256` from an evaluated `license_reviews` item into `review.license_decisions`. Each record requires `decided_by`, timezone-aware `decided_at`, `reason`, and `conditions`; `expires_at` is optional. This records your decision, not a new automatic allow grade. Exact evidence and assessment matching is required. Do not invent a reviewer or silently accept on a user's behalf. Keep the policy outside untrusted target projects and select it explicitly.

```json
{"finding_sha256":"<copy the 64-character finding hash>",
 "decided_by":"Your reviewer name","decided_at":"2026-11-22T10:00:00Z",
 "reason":"Explain the reviewed use and evidence",
 "conditions":"State the conditions you will follow"}
```

The placeholder above is deliberately invalid until replaced. Unresolved license evidence cannot be cleared by an acceptance record. Expired, future or nonmatching records remain visible and are not counted as applied. No identity or authority is authenticated.

Reassess an existing review with your selected policy without contacting any upstream service:

```sh
uv run --frozen --project plugins/oss-gate python plugins/oss-gate/cli.py \
  --policy /absolute/policy.json reassess /absolute/review-directory \
  --output-root /absolute/new-reviews
```

Write a new narrative for the returned folder, then render it. The source review is unchanged. The new snapshot seals the selected configuration, evaluation time, source data and applicable decisions. The names, reasons and conditions become part of the report: inspect them before sharing.
