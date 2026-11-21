# v0.4.2 validation record

This release adds optional additional PEM CA certificates through `network.additional_ca_file` for HTTPS-inspecting networks. Both synchronous API requests and asynchronous DeepWiki requests use the selected trust configuration. The default certifi roots remain trusted; certificate chain, hostname and expiry verification remain enabled. Ambient proxy and certificate environment variables remain disabled.

Custom connection pools are scoped to one operation, including its dependency workers. Invalid, missing, oversized or private-key-containing CA files stop the operation with a safe configuration error. An additional CA does not bypass identifier policies, service restrictions, repository-host checks, response bounds or redirect restrictions. Review evidence records the SHA-256 of the loaded file and the certifi version.

The policy uses an explicit absolute local file path. Offline evaluation and rendering do not require the original CA file. The selected policy retained in evidence contains this local path, so review it before sharing evidence. See [customization](customization.md#additional-ca-certificates) for configuration and scope.

## Validation

On 2026-11-21, local Python 3.10 and 3.13 each passed 93 unittest tests. Ten additional tests exercise real ephemeral local TLS connections, additive CA trust, rejection without selected trust, hostname and expiry failures, synchronous and asynchronous clients, concurrent operation isolation, worker context propagation, malformed settings, safe errors, policy enforcement, sealed evidence, offline rendering and resistance to ambient CA/proxy overrides. Test CAs are temporary and are never installed in the operating system trust store.

Ruff, both MCP adapters, CLI distribution parity, bilingual examples, 18 static pages and release packaging are checked before publication. The required GitHub Actions matrix covers Ubuntu 3.10/3.13, macOS 3.13 and Windows 3.13 before merging.

Certifi is now an explicit pinned dependency; it was already present transitively at the same version. No third-party package/version pins changed from v0.4.1. The prior dependency self-review is documented in [v0.4.1](release-v0.4.1.md); it is not a new vulnerability scan for this release.

This release does not add native OS trust-store integration, proxy routing, client certificates or trust configuration for uv dependency installation. No real corporate network was available for validation. Local TLS regression tests do not establish compatibility with every enterprise network and are not a security certification.
