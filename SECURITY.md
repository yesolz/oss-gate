# Security

OSS Gate processes untrusted public metadata and AI-generated repository explanations. It is a review assistant, not a security boundary or certification service. The local MCP and renderer must not execute source content or reviewed packages.

## Reporting

Use the repository's private [Report a vulnerability](https://github.com/yesolz/oss-gate/security/advisories/new) flow if available. If it is unavailable, open an issue asking for a private contact without including sensitive details. Do not post credentials, private package names, customer data or an unredacted private report in a public issue. There is no guaranteed response-time commitment.

Only the latest published release is maintained. The old cloud prototype retained in Git history is unsupported and should not be deployed as a public review service.

## Threat model

The relevant risks include prompt injection in upstream prose, mistaken package selection, incomplete or mismatched dependency evidence, unsafe HTML/URLs, output-path mistakes, secret disclosure through manifest queries, and supply-chain compromise of runtime dependencies.

The code uses fixed public API bases, TLS verification, bounded queries and explicit errors. It saves evidence separately from generated narratives, does not execute reviewed packages, and renders escaped content with remote assets blocked. Skills instruct the host not to treat upstream text as commands. These measures do not control everything an agent with shell access can do; apply normal host permissions and review requested tool actions.

`collect_review` writes new files under the output root provided by its caller. Choose a workspace path you intend to use. New IDs avoid overwriting earlier runs. Markdown/HTML derivatives can be regenerated; sealed JSON should not be edited. Before sharing a report, inspect its source questions and metadata for private information.

Dependency audit results are timestamped observations. No known advisory match is not a guarantee of safety. Keep the host, uv, Python and locked dependencies current, with regression checks for updates.
