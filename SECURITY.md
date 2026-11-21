# Security

OSS Gate processes untrusted public metadata and AI-generated repository explanations. It is a review assistant, not a security boundary or certification service. The local MCP and renderer must not execute source content or reviewed packages.

## Reporting

Use the repository's private [Report a vulnerability](https://github.com/yesolz/oss-gate/security/advisories/new) flow if available. If it is unavailable, open an issue asking for a private contact without including sensitive details. Do not post credentials, private package names, customer data or an unredacted private report in a public issue. There is no guaranteed response-time commitment.

Only the latest published release is maintained. Archived workshop prototypes are unsupported and should not be deployed as public review services.

## Threat model

The relevant risks include prompt injection in upstream prose, mistaken package selection, incomplete or mismatched dependency evidence, unsafe HTML/URLs, output-path mistakes, secret disclosure through manifest queries, and supply-chain compromise of runtime dependencies.

The code uses fixed public API bases, TLS verification, bounded queries and explicit errors. It saves evidence separately from generated narratives, does not execute reviewed packages, and renders escaped content with remote assets blocked. Skills instruct the host not to treat upstream text as commands. These measures do not control everything an agent with shell access can do; apply normal host permissions and review requested tool actions.

`collect_review` writes new files under the output root provided by its caller. Choose a workspace path you intend to use. New IDs avoid overwriting earlier runs. Markdown/HTML derivatives can be regenerated; sealed JSON should not be edited. Before sharing a report, inspect its source questions and metadata for private information.

API and DeepWiki HTTP bodies are limited to 16 MiB per response before JSON or SSE parsing. Requests ask for uncompressed bodies and reject unexpected content encodings. Streaming responses have a 120-second elapsed-time check between chunks, in addition to socket timeouts; a DeepWiki operation is cancelled after 120 seconds. Limit failures remain incomplete evidence, never a clean result or proof that a package is absent. These bounds are not a total process-memory quota: parsed objects, concurrent queries, accumulated evidence and local files still consume memory. Use trusted endpoints and host-level resource limits when processing untrusted evidence.

Dependency audit results are timestamped observations. No known advisory match is not a guarantee of safety. Keep the host, uv, Python and locked dependencies current, with regression checks for updates.

## Optional local policy

Explicitly selected settings can restrict service destinations and package/repository identifiers before outbound calls. Both bundled MCP adapters and CLI entry points apply these checks. No settings are discovered from the target repository. The local DeepWiki adapter sends fixed topic questions, connects only when called and does not follow redirects. Existing direct remote DeepWiki connections must be replaced to use these controls.

These checks do not sandbox the host agent, protect a policy file from its owner, or govern other tools, model-provider traffic or dependency installation. Use host permissions and organization network controls when mandatory enforcement is required. Deny patterns cannot recognize every private identifier; strict setups need a locally defined allowlist. A blocked dependency may leave its entire OSV batch unqueried.

Additional review policies preserve base restrictions. Communication assertions require explicit reviewer-provided provenance, but the program cannot independently verify the truth of that attribution or its completeness. Do not treat AI-generated statements or an empty observation list as proof of no network behavior. Saved reports can include organization settings, reviewer attribution and queries; inspect all files before sharing.

Repository-host restrictions inspect the repository identifier being sent, including upstream-discovered projects, independently of the API server hostname. Unspecified host restrictions preserve defaults; strict deployments should explicitly set an allowlist. DeepWiki remains limited to public GitHub repositories.

An explicit npm mirror URL grants only metadata reads under that exact HTTPS origin and base path, subject to existing service and identifier rules. It is not a general outbound-host grant. Redirects and public fallback are disabled. Keep policy files trusted: choosing an internal mirror authorizes contact with that address. Credentials in URLs, automatic credential discovery and TLS bypass are unsupported. Mirror evidence may be stale or filtered and does not establish public absence, package-byte identity or safety.

## Repository and release controls

The GitHub repository requires a pull request and the four platform CI checks before merging into `main`, including for administrators. Force pushes and branch deletion are blocked. A second person's approving review is not mandatory while the project has one maintainer; external contributions still require maintainer inspection. All external contributors require approval before their fork PR workflows run. Read the proposed code and workflow changes before approving a run, and do not test untrusted contributions in a local environment containing credentials.

Version tags matching `v*` cannot be updated or deleted under the active ruleset. GitHub Actions must use full commit SHAs. CI does not retain checkout credentials, has bounded job durations and uses read-only repository permissions. Only the Pages deployment job receives Pages write and OIDC permissions, and the deployment environment allows `main` only.

Secret scanning, push protection, private vulnerability reporting, Dependabot alerts and security updates are enabled in repository settings. A weekly and manually runnable dependency audit also checks both runtime and development lockfiles. Audit failures require maintainer triage; updates are not automatically merged. GitHub's dependency coverage and secret detectors are incomplete, and a clean scan is not proof that no secret or vulnerability exists.

These settings are server-side controls, not files included in a clone. Repository administrators can change them. Protect maintainer accounts with a passkey or strong two-factor authentication, keep recovery codes offline, and use narrowly scoped, expiring tokens. A checksum detects changed bytes but is not independent publisher authentication; an attacker who controls the account may replace both an artifact and its published checksum. Report evidence hashes likewise detect changes relative to their manifest, not the identity or honesty of whoever created that manifest.
