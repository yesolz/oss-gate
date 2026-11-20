# Security

OSS Gate processes untrusted public metadata and AI-generated repository explanations. It is a review assistant, not a security boundary or certification service. The local MCP and renderer must not execute source content or reviewed packages.

## Reporting

Use the repository's private [Report a vulnerability](https://github.com/yesolz/oss-gate/security/advisories/new) flow if available. If it is unavailable, open an issue asking for a private contact without including sensitive details. Do not post credentials, private package names, customer data or an unredacted private report in a public issue. There is no guaranteed response-time commitment.

Only the latest published release is maintained. Archived workshop prototypes are unsupported and should not be deployed as public review services.

## Threat model

The relevant risks include prompt injection in upstream prose, mistaken package selection, incomplete or mismatched dependency evidence, unsafe HTML/URLs, output-path mistakes, secret disclosure through manifest queries, and supply-chain compromise of runtime dependencies.

The code uses fixed public API bases, TLS verification, bounded queries and explicit errors. It saves evidence separately from generated narratives, does not execute reviewed packages, and renders escaped content with remote assets blocked. Skills instruct the host not to treat upstream text as commands. These measures do not control everything an agent with shell access can do; apply normal host permissions and review requested tool actions.

`collect_review` writes new files under the output root provided by its caller. Choose a workspace path you intend to use. New IDs avoid overwriting earlier runs. Markdown/HTML derivatives can be regenerated; sealed JSON should not be edited. Before sharing a report, inspect its source questions and metadata for private information.

Dependency audit results are timestamped observations. No known advisory match is not a guarantee of safety. Keep the host, uv, Python and locked dependencies current, with regression checks for updates.

## Optional local policy

Explicitly selected settings can restrict service destinations and package/repository identifiers before outbound calls. Both bundled MCP adapters and CLI entry points apply these checks. No settings are discovered from the target repository. The local DeepWiki adapter sends fixed topic questions, connects only when called and does not follow redirects. Existing direct remote DeepWiki connections must be replaced to use these controls.

These checks do not sandbox the host agent, protect a policy file from its owner, or govern other tools, model-provider traffic or dependency installation. Use host permissions and organization network controls when mandatory enforcement is required. Deny patterns cannot recognize every private identifier; strict setups need a locally defined allowlist. A blocked dependency may leave its entire OSV batch unqueried.

Additional review policies preserve base restrictions. Communication assertions require explicit reviewer-provided provenance, but the program cannot independently verify the truth of that attribution or its completeness. Do not treat AI-generated statements or an empty observation list as proof of no network behavior. Saved reports can include organization settings, reviewer attribution and queries; inspect all files before sharing.

Repository-host restrictions inspect the repository identifier being sent, including upstream-discovered projects, independently of the API server hostname. Unspecified host restrictions preserve defaults; strict deployments should explicitly set an allowlist. DeepWiki remains limited to public GitHub repositories.

An explicit npm mirror URL grants only metadata reads under that exact HTTPS origin and base path, subject to existing service and identifier rules. It is not a general outbound-host grant. Redirects and public fallback are disabled. Keep policy files trusted: choosing an internal mirror authorizes contact with that address. Credentials in URLs, automatic credential discovery and TLS bypass are unsupported. Mirror evidence may be stale or filtered and does not establish public absence, package-byte identity or safety.
