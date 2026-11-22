# requests 2.34.2: Open-source adoption review

Snapshot date: 2026-11-17T00:00:00Z · pypi · psf/requests · oss-gate.policy/3

> Historical example. The source snapshot is preserved; the verdict shown here is reassessed using policy v3. This is not a live scan.

**Verdict: Conditional**

Requests is a Python HTTP client for services that need readable code for calling external APIs. Its own Apache-2.0 metadata passes the project's screening policy. The adoption question in this snapshot is the MPL-2.0 license of the direct dependency certifi, which makes the result conditional. Review the actual distribution and modification of that component before recording a human adoption decision.

## 1. Decision and scope

| Area | Verdict |
|---|---|
| License | Conditional |
| Known vulnerabilities | Allow |
| Dependencies | Allow |
| Maintenance | Allow |

A screening aid, not a legal opinion or security certification. Public metadata can be incomplete. DeepWiki narratives are AI-generated and may not describe the reviewed version.

Historical verdict: `Conditional`. The table above applies policy v3 to the same saved evidence.

## 2. What the software does

Requests wraps HTTP operations in a small API for methods, parameters, JSON, form data, uploads, streaming, authentication, cookies and sessions. The saved DeepWiki material describes connection pooling and keep-alive through urllib3, TLS verification, Basic/Digest authentication and automatic response decoding. These descriptions are AI-generated repository summaries, not observations of the reviewed version running in a test environment. [Source: `data.json#/deepwiki`]

A call to `Session.request` builds a `Request`, prepares it as a `PreparedRequest`, and merges session settings such as cookies, headers, authentication and hooks. `prepare_body` handles the body format. `merge_environment_settings` contributes proxy and TLS settings; `Session.send` selects an `HTTPAdapter`, which delegates network work to urllib3. The returned `Response` passes through hooks, cookie handling and redirect processing. Adapters can be mounted for custom transport behavior. [Source: saved DeepWiki request-flow answers]

The historical usage example is `requests.get(url, params=..., auth=...)`, with `json=...` for a JSON body and a `Session` for persistent settings. The wiki describes Python 3.10 or later and PyPy support. Verify runtime compatibility against the exact release before adopting it; the wiki is not version-pinned.

## 3. External communication and configuration

The core purpose is to send requests to destinations supplied by the application. Depending on the call, those requests can contain URLs, headers, credentials, cookies and body data. The examined wiki material did not identify separate product telemetry; that limited observation does not establish that every code path is free of additional communication. [Source: saved DeepWiki communication answer]

The saved material describes `trust_env=True` by default, with proxy environment variables (`http_proxy`, `https_proxy`, `no_proxy`, `all_proxy`), `REQUESTS_CA_BUNDLE`, fallback `CURL_CA_BUNDLE`, and `.netrc` affecting requests. Review the deployment environment and set `Session.trust_env=False` when those ambient settings are unwanted. Keep TLS verification enabled. For a private CA, inspect the release-specific support for `verify=<path>` or a CA bundle setting. [Source: saved DeepWiki settings answer]

Client certificate/private-key handling needs its own file-permission and secret-storage review. The historical wiki said the client key must be unencrypted; that statement was not independently exercised here. A redirect claim about removing authentication headers on a host change was not reproduced during the original agent recheck, so it must not be treated as a tested security guarantee. No credential values are included in this example.

## 4. License review

`requests@2.34.2`: Apache-2.0.

Categories are screening outcomes, not legal conclusions. `unknown` includes missing metadata, unsupported identifiers and uninterpreted exceptions. A list with an unspecified relationship is conservatively reviewed as AND; an OR choice must be selected and documented.

| Package | Version | License | Category | Dependency path |
|---|---|---|---|---|
| certifi | 2026.10.23 | MPL-2.0 | weak-copyleft | requests@2.34.2 → certifi@2026.10.23 |
| charset-normalizer | 3.5.2 | MIT | permissive | requests@2.34.2 → charset-normalizer@3.5.2 |
| idna | 3.20.0 | BSD-3-Clause | permissive | requests@2.34.2 → idna@3.20.0 |
| urllib3 | 2.8.0 | MIT | permissive | requests@2.34.2 → urllib3@2.8.0 |

## 5. Known vulnerabilities

No known advisories were returned in this snapshot. This is not proof of absence.

Connected aliases count as one group. Titles are source text. Missing severity is not a zero score. A list of fixed versions is not an upgrade recommendation until the affected package and branch have been matched.

## 6. Dependencies

Direct: 4 · Transitive: 0 · graph version: `2.34.2`

The four direct dependencies in the saved graph have distinct roles: certifi supplies CA certificates, charset-normalizer handles character encoding detection, idna supports internationalized domain names, and urllib3 provides connection pooling and HTTP transport. These roles come from AI-generated DeepWiki explanations; the exact package versions and graph paths come from deps.dev. [Sources: `data.json#/deepwiki`, `data.json#/get_dependencies`]

Optional extras change the reviewed scope. The historical explanation identifies `socks` with PySocks and `use_chardet_on_py3` with chardet; it says chardet can take precedence over charset-normalizer when installed. Those extra packages are not covered by the four-node dependency snapshot. The `security` extra was described as empty. Check the exact package metadata before enabling extras or relying on that behavior.

| Parent | Child |
|---|---|
| requests@2.34.2 | certifi@2026.10.23 |
| requests@2.34.2 | charset-normalizer@3.5.2 |
| requests@2.34.2 | idna@3.20.0 |
| requests@2.34.2 | urllib3@2.8.0 |

## 7. Maintenance

The saved Scorecard is dated 2026-08-24, which was 85 days before the original review date. It is a dated signal, not a measurement of the current repository. Maintained is 10, Code-Review is 8, and Security-Policy is 10; Pinned-Dependencies is 5, while Signed-Releases and CII-Best-Practices are 0. Branch-Protection is -1 because it could not be evaluated, and there is no Vulnerabilities check in the response. A PyPI attestation link and the Signed-Releases score concern different evidence and were not reconciled in the old review. [Source: `data.json#/get_project/scorecard`]

The historical narrative describes maintenance under the psf organization and a private security-advisory reporting process. It also mentions response and remediation targets, but these were not independently confirmed here and are not service guarantees. The original recheck did not reproduce a claimed security-document link. Read the current upstream security policy when reporting an actual vulnerability. [Source: saved DeepWiki maintenance answer]

| Check | Score | Source details |
|---|---|---|
| Code-Review | 8 | Found 11/13 approved changesets -- score normalized to 8 |
| Security-Policy | 10 | security policy file detected |
| Dangerous-Workflow | 10 | no dangerous workflow patterns detected |
| Maintained | 10 | 26 commit(s) and 7 issue activity found in the last 90 days -- score normalized to 10 |
| Binary-Artifacts | 10 | no binaries found in the repo |
| Token-Permissions | 10 | GitHub workflow tokens follow principle of least privilege |
| Pinned-Dependencies | 5 | dependency not pinned by hash detected -- score normalized to 5 |
| CII-Best-Practices | 0 | no effort to earn an OpenSSF best practices badge detected |
| Fuzzing | 10 | project is fuzzed |
| License | 10 | license file detected |
| Signed-Releases | 0 | Project has not signed or included provenance with any releases. |
| Branch-Protection | -1 | internal error: error during branchesHandler.setup: internal error: some github tokens can't read classic branch protection rules: https://github.com/ossf/scorecard-action/blob/main/docs/authenticatio… |
| Packaging | 10 | packaging workflow detected |
| SAST | 10 | SAST tool is run on all commits |

## 8. Adoption actions

1. Record a human decision about certifi's MPL-2.0 obligations in the intended distribution. Identify whether certifi files are modified, whether the CA bundle is redistributed, and which artifacts are shipped. The screening category alone cannot answer those questions.
2. Compare the actual environment's lockfile to every version in the evidence table. Pin and hash the chosen environment, then review again if a version or extra changes.
3. Review proxy/CA settings and `.netrc` behavior. Keep TLS verification enabled and protect any client-key files through the deployment's secret-management process.
4. Review the optional PySocks/chardet dependencies before enabling the corresponding extras.
5. Refresh outdated maintenance and vulnerability evidence before a production decision. A translated historical report is not a fresh query.

## 9. Unknowns and limitations

Coverage gaps: No additional machine coverage flag. Narrative limitations below still apply.

The original agent evidence review was WARN. It reported no grade-affecting disagreement, but several supporting claims were not reproduced: a license-related explanation for replacing charset-normalizer, a security-document link and redirect authentication-header behavior. A package-candidate count was corrected from 15 to 14. Several wiki questions and the repository table of contents were not rechecked.

The graph was not compared to an installed environment or independently reconstructed from package artifacts. The wiki is not pinned to Requests 2.34.2. The Scorecard was already 85 days old when the snapshot was collected. No current vulnerability or license query is performed while generating this example.

## 10. Evidence and verification

| Claim | Source |
|---|---|
| License | data.json#/lookup_package/licenses |
| Dependencies | data.json#/get_dependencies |
| Known vulnerabilities | data.json#/advisories |
| Maintenance | data.json#/get_project/scorecard |
| DeepWiki | data.json#/deepwiki |

Verification status: **WARN**. The original JSON hash, policy calculation and bilingual numerical tables are checked. This does not freshly authenticate the old external responses or verify every wiki assertion.

SHA-256 (`data.json`): `af943908340f5c6db720679a8f4f2473b43e91cfc39bf9a332f838c4648ddb3d`

[deps.dev](https://deps.dev/) · [OSV](https://osv.dev/) · [DeepWiki](https://deepwiki.com/psf/requests)

See [NOTICE](../../NOTICE.md) for source attribution and terms.
