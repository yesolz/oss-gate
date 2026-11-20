# Optional execution and policies

Ordinary plugin use needs no settings. Both local MCP adapters and the CLI share evidence and policy functions. Select a mode explicitly; do not register MCP tools solely to run the CLI. Rendering and policy evaluation use saved evidence without network access, but initial uv/runtime setup may download dependencies.

## CLI mode

From a checkout, replace `<plugin-root>` with its absolute path. The user can provide the same path for a stable installed plugin. Run `cli.py --help` for available commands. CLI mode still uses the user's agent for narrative writing; it does not call a model API to write a report.

```sh
uv run --frozen --project "<plugin-root>" python "<plugin-root>/cli.py" plan pypi requests --version 2.34.2 --repo psf/requests
uv run --frozen --project "<plugin-root>" python "<plugin-root>/cli.py" collect pypi requests --version 2.34.2 --output-root /absolute/reviews
uv run --frozen --project "<plugin-root>" python "<plugin-root>/cli.py" explain psf/requests --topic overview --out /absolute/review/deepwiki.json
uv run --frozen --project "<plugin-root>" python "<plugin-root>/cli.py" render /absolute/review --language both
```

`plan` is a local preview of initial destinations, not a complete list of future dependency/advisory requests. Every later request is checked separately. `collect` saves full evidence and prints the verdict and file paths. Write `review.ko.md` and/or `review.en.md` from that evidence before `render`. `explain` saves the complete response in a new file in an existing directory. Multiple topics need separate filenames. It accepts only `overview`, `communication`, `dependencies` and `maintenance`. Errors return a nonzero CLI exit code; a completed hold verdict is not an execution error.

## Selecting policy

MCP: set `OSS_GATE_POLICY` to an absolute settings JSON path in both local MCP servers' environment, then restart them. CLI: use `--policy /absolute/settings.json` before the subcommand, or the same environment variable. A different CLI path cannot replace an environment-selected policy. No file is automatically discovered from a repository or working directory. Never remove or change a selected policy to complete a blocked task.

`policies/example.json` is an opt-in illustration, not a product default or recommended organization standard. It disables DeepWiki, blocks example internal namespaces, requires communication evidence and selects a seven-day release waiting period. Copy and edit it only when the user asks. Omitted network settings preserve existing services; `services: []` blocks all service calls. Identifier patterns use `npm:`, `pypi:`, `go:`, `maven:`, `cargo:`, `nuget:`, `rubygems:` or `repo:` prefixes. Repository values are `owner/repo`, without `github.com/`. Deny patterns take precedence. An explicit `allow_identifiers: []` allows no package or repository identifiers; omission means no allowlist. An allowlist does not restrict advisory IDs. Scoped npm names are not inherently private. Public availability cannot be inferred without sending the identifier, so strict setups must define their own local allowlist.

The core normalizes PyPI punctuation/case and npm/NuGet/repository case for comparisons. Patterns use shell-style matching; a `*` can match `/`. Every returned dependency is checked too. One blocked identifier blocks the whole OSV batch, conservatively leaving all batch members unverified. Blocked/error coverage can never become a clean review.

## Additional review rules

The optional result can only maintain or increase the base outcome's restrictions. Saved policy content, SHA-256 and evaluation time are sealed with the evidence. Rendering uses that saved context, not current configuration or wall-clock time. Do not edit it to reassess a report. Existing reports without policy context retain the base behavior. Portfolio comparison rejects mixed additional policies.

- `minimum_release_age_days` is an integer from 0 to 3650, default 0. A younger release is conditional. Missing/invalid/future publication times remain unverified. This does not measure project abandonment. Urgent security fixes may require an explicit human decision; the tool does not silently exempt them or recommend keeping a vulnerable version.
- `require_communication_review` defaults to false. If enabled, missing, partial, unverified, future-dated or wrong-version communication evidence is conditional.
- `blocked_destinations` contains lowercase hostnames or `*.host` patterns (the latter matches subdomains, not the apex). Reviewed evidence that a matching destination is required or enabled by default yields hold. Unknown activation conditions yield conditional. An explicitly optional, default-disabled destination does not itself block. This describes upstream defaults, not the actual deployed configuration.

`communication_path` on `collect_review`, or CLI `collect --communication`, takes an absolute JSON file path. The schema example is `policies/communication.example.json`. A reviewed record needs exact ecosystem/name/version, `status: reviewed`, `coverage: complete` for a complete review, `reviewed_by`, timezone-qualified `reviewed_at`, HTTPS source links and observations. An empty observation list with complete reviewed coverage is an explicit reviewer assertion of no identified outbound communication, not an inference from an empty API result. Preserve the reviewer-provided attribution and limitations. Do not promote DeepWiki text or model guesses to reviewed evidence, impersonate a reviewer or fabricate review dates. Communication observations currently represent HTTP(S) destinations. If other transports or unresolved destinations are relevant, keep coverage partial. The program validates structure and applicability, not the truth of an attestation. If evidence is not available, keep the conditional result; do not manufacture a record to pass.

## Boundaries

This is per-tool policy enforcement, not a sandbox for the host agent. Other MCPs, browser tools, shell commands, model-provider traffic and uv setup are outside its control. Users who can modify the code, environment or policy file can bypass it; organizations must protect those through their own host controls. Existing direct remote DeepWiki connections bypass the local adapter and must be removed from a restricted setup. Reports and settings can contain organization names and reviewer details: inspect them before sharing. No centralized logs, telemetry, policy server or new model credentials are introduced.
