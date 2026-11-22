# Optional execution and policies

Ordinary plugin use needs no settings. Both local MCP adapters and the CLI share evidence and policy functions. Select a mode explicitly; do not register MCP tools solely to run the CLI. Rendering and policy evaluation use saved evidence without network access, but initial uv/runtime setup may download dependencies.

## CLI mode

From a checkout, replace `<plugin-root>` with its absolute path. The user can provide the same path for a stable installed plugin. Run `cli.py --help` for available commands. CLI mode still uses the user's agent for narrative writing; it does not call a model API to write a report.

```sh
uv run --frozen --project "<plugin-root>" python "<plugin-root>/cli.py" project psf/requests --out /absolute/project.json
uv run --frozen --project "<plugin-root>" python "<plugin-root>/cli.py" audit /absolute/sanitized-requirements.txt --type requirements.txt --out /absolute/audit.json
uv run --frozen --project "<plugin-root>" python "<plugin-root>/cli.py" plan pypi requests --version 2.34.2 --repo psf/requests
uv run --frozen --project "<plugin-root>" python "<plugin-root>/cli.py" collect pypi requests --version 2.34.2 --output-root /absolute/reviews
uv run --frozen --project "<plugin-root>" python "<plugin-root>/cli.py" explain psf/requests --topic overview --out /absolute/review/deepwiki.overview.json
uv run --frozen --project "<plugin-root>" python "<plugin-root>/cli.py" render /absolute/review --language both
```

`project` saves full repository metadata and package candidates; verify identity before selecting one. `audit` saves the direct-dependency audit of a locally inspected, sanitized file (`package.json`, `requirements.txt` or `go.mod`). Both require a new `--out` path in an existing directory. Neither installs or executes the target.

`plan` is a local preview of initial destinations, not a complete list of future dependency/advisory requests. Every later request is checked separately. `collect` saves full evidence and prints the verdict and file paths. Write `review.ko.md` and/or `review.en.md` from that evidence before `render`. `explain` saves the complete response, including failures, in a new file in an existing directory. Multiple topics need separate filenames. Use `index-explanations` and `record-verification` as shown in `evidence-files.md`; these local writers are available in both plugin variants. It accepts only `overview`, `communication`, `dependencies` and `maintenance`. Errors return a nonzero CLI exit code; a completed hold verdict is not an execution error.

## Selecting policy

MCP: set `OSS_GATE_POLICY` to an absolute settings JSON path in both local MCP servers' environment, then restart them. CLI: use `--policy /absolute/settings.json` before the subcommand, or the same environment variable. A different CLI path cannot replace an environment-selected policy. No file is automatically discovered from a repository or working directory. Never remove or change a selected policy to complete a blocked task.

`policies/example.json` is an opt-in illustration, not a product default or recommended organization standard. It disables DeepWiki, blocks example internal namespaces, requires communication evidence and selects a seven-day release waiting period. Copy and edit it only when the user asks. Omitted network settings preserve existing services; `services: []` blocks all service calls. Identifier patterns use `npm:`, `pypi:`, `go:`, `maven:`, `cargo:`, `nuget:`, `rubygems:` or `repo:` prefixes. GitHub repository patterns use `owner/repo` (an optional `github.com/` prefix is normalized away). Other hosts retain `host/owner/repo`, including nested groups. For example, `repo:company/*` matches a GitHub organization, while `repo:*.example.internal/*` matches repositories on subdomains of example.internal. Deny patterns take precedence. An explicit `allow_identifiers: []` allows no package or repository identifiers; omission means no allowlist. An allowlist does not restrict advisory IDs. Scoped npm names are not inherently private. Public availability cannot be inferred without sending the identifier, so strict setups must define their own local allowlist.

The core normalizes PyPI punctuation/case and npm/NuGet/repository case for comparisons. Patterns use shell-style matching; a `*` can match `/`. Every returned dependency is checked too. One blocked identifier blocks the whole OSV batch, conservatively leaving all batch members unverified. Blocked/error coverage can never become a clean review.

## Repository hosts and npm mirrors

`network.allowed_repository_hosts` is an optional list of exact hostnames, such as `["github.com"]`. Omission keeps existing behavior; `[]` blocks repository-bearing requests. Hostnames are normalized for case, a trailing dot and IDNA, and must not contain wildcards, ports or URL paths. This controls the repository identity sent to deps.dev or DeepWiki, not the API destination. It applies to discovered repositories too. Service and identifier restrictions still apply. DeepWiki supports public GitHub repositories only; an allowed enterprise host does not add provider support.

`network.npm_registry_url` optionally replaces public npm for existence diagnostics after a deps.dev 404. It accepts an HTTPS origin with an optional port and base path, for example `https://registry.example.internal/repository/npm/`. It is controlled by the existing `npm` service and package identifier rules. Only metadata paths under that exact base are allowed; redirects and public npm fallback are disabled. `plan` displays the selected base without contacting it. See `policies/npm-mirror.example.json`.

Mirrors must expose npm-compatible package and exact-version JSON endpoints without credentials supplied by OSS Gate. URL credentials, query strings and fragments are rejected. No `.npmrc`, credential discovery, custom authentication or TLS bypass is provided. Authentication/access failures remain unverified. A mirror 404 is scoped to that mirror and can reflect lag or access policy; it does not establish public nonexistence. A mirror hit does not replace deps.dev evidence, verify identical package bytes, or imply approval. If deps.dev is unavailable rather than returning 404, the mirror is not queried. OSV, deps.dev and optional DeepWiki remain external services; this does not enable fully disconnected analysis. PyPI mirror support is outside this release.

## Additional review rules

The optional result can only maintain or increase the base outcome's restrictions. Saved policy content, SHA-256 and evaluation time are sealed with the evidence. Rendering uses that saved context, not current configuration or wall-clock time. Do not edit it to reassess a report. Existing reports without policy context retain the base behavior. Portfolio comparison rejects mixed additional policies.

- `minimum_release_age_days` is an integer from 0 to 3650, default 0. A younger release is conditional. Missing/invalid/future publication times remain unverified. This does not measure project abandonment. Urgent security fixes may require an explicit human decision; the tool does not silently exempt them or recommend keeping a vulnerable version.
- `require_communication_review` defaults to false. If enabled, missing, partial, unverified, future-dated or wrong-version communication evidence is conditional.
- `blocked_destinations` contains lowercase hostnames or `*.host` patterns (the latter matches subdomains, not the apex). Reviewed evidence that a matching destination is required or enabled by default yields hold. Unknown activation conditions yield conditional. An explicitly optional, default-disabled destination does not itself block. This describes upstream defaults, not the actual deployed configuration.

`communication_path` on `collect_review`, or CLI `collect --communication`, takes an absolute JSON file path. The schema example is `policies/communication.example.json`. A reviewed record needs exact ecosystem/name/version, `status: reviewed`, `coverage: complete` for a complete review, `reviewed_by`, timezone-qualified `reviewed_at`, HTTPS source links and observations. An empty observation list with complete reviewed coverage is an explicit reviewer assertion of no identified outbound communication, not an inference from an empty API result. Preserve the reviewer-provided attribution and limitations. Do not promote DeepWiki text or model guesses to reviewed evidence, impersonate a reviewer or fabricate review dates. Communication observations currently represent HTTP(S) destinations. If other transports or unresolved destinations are relevant, keep coverage partial. The program validates structure and applicability, not the truth of an attestation. If evidence is not available, keep the conditional result; do not manufacture a record to pass.

## Boundaries

This is per-tool policy enforcement, not a sandbox for the host agent. Other MCPs, browser tools, shell commands, model-provider traffic and uv setup are outside its control. Users who can modify the code, environment or policy file can bypass it; organizations must protect those through their own host controls. Existing direct remote DeepWiki connections bypass the local adapter and must be removed from a restricted setup. Reports and settings can contain organization names and reviewer details: inspect them before sharing. No centralized logs, telemetry, policy server or new model credentials are introduced.

## Explicit additional CA trust

`network.additional_ca_file` optionally adds public PEM CA certificates to certifi for all OSS Gate HTTP clients, including DeepWiki and configured mirrors. Use an absolute local path (at most 1 MiB, no private keys). Only select a CA supplied by the user or their administrator; never create, download or substitute a CA to bypass an upstream certificate error. TLS verification stays enabled, ambient proxy/CA variables remain disabled, and service/identifier restrictions still apply.

An invalid or missing CA file returns `tls_configuration_invalid` before collection; do not remove the setting and retry. `plan` checks syntax without opening the file. Collection records the loaded file hash and certifi version in sealed `tls_trust` evidence. The saved policy includes its local path, so check sharing scope. Offline rendering never loads the file. OS trust-store integration, proxy routing, client certificates and uv bootstrap configuration are outside this setting. See the customization guide.

## License classification and reviewer decisions

Policy/3 distinguishes missing license metadata, unclassified SPDX IDs, custom references, unsupported exceptions and malformed input. A known ID is not automatic permission. Read `verdict.license_reviews` for the selected OR branch, reason, notes and exact finding hash. Explain what the user should check; do not describe every hold as a known legal violation.

Explicit settings may add `review.license_restrictions` (exact SPDX ID to conditional/hold) and `review.license_decisions` (finding_sha256, decided_by, decided_at, reason, conditions, optional expires_at). Decisions never alter the automatic verdict or clear unrelated findings. Never manufacture acceptance or reviewer attribution. A recorded decision is not an authenticated approval. Unknown, nonmatching, future and expired records do not count as applied.

To apply explicit settings to saved evidence offline, run `cli.py --policy /absolute/policy.json reassess /absolute/review --output-root /absolute/new-reviews`. This creates new sealed data and preserves source-data.json. Write a fresh narrative in the returned folder before rendering. Do not rewrite sealed inputs or copy an old narrative as if it reflected the new policy. The same CLI is bundled in both distributions.
