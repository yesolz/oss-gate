# next 16.4.6: Open-source adoption review

Snapshot date: 2026-11-17T00:00:00Z · npm · vercel/next.js · oss-gate.policy/3

> Historical example. The source snapshot is preserved; the verdict shown here is reassessed using policy v3. This is not a live scan.

**Verdict: Conditional**

Next.js combines React routing, server rendering, server features and build tooling. Both saved versions require adoption review because of dependency-license questions. Version 15.1.0 additionally has known high-severity vulnerabilities in the package and its dependency graph. These dated examples show how the same framework can present different findings by version; neither report is a recommendation to install an old release today.

## 1. Decision and scope

| Area | Verdict |
|---|---|
| License | Conditional |
| Known vulnerabilities | Allow |
| Dependencies | Allow |
| Maintenance | Conditional |

A screening aid, not a legal opinion or security certification. Public metadata can be incomplete. DeepWiki narratives are AI-generated and may not describe the reviewed version.

Historical verdict: `Hold`. The table above applies policy v3 to the same saved evidence.

## 2. What the software does

The historical DeepWiki narrative describes App Router and Pages Router, server-rendered React applications and integrated compilation/build tooling. It discusses Turbopack, caching and partial prerendering, but the repository wiki is not bound to the requested package version. In particular, descriptions of newer Next.js behavior must not be assumed to apply to 15.1.0. [Source: historical review narrative; saved `data.json#/deepwiki` where available]

The repository is described as a pnpm monorepo with the framework in `packages/next`, native code in `crates` and Turbopack sources in `turbopack`. CLI entry points include `next-dev.ts`, `next-build.ts` and `next-start.ts`. The request-flow explanation goes through `router-server.ts`, `resolveRoutes`, `BaseServer`, route matching and an App/Page module or route handler. Request-scoped URL, header and cookie data are used during rendering. The full Edge Proxy conversion path was not established by the excerpts.

The compilation explanation describes Rust SWC transforms, including server actions and React Server Components, with NAPI bindings and a separate WASM build. Native package selection and some runtime loading details were not confirmed. The original getting-started narrative gave `pnpm create next-app@latest my-app --yes`, followed by `pnpm dev`, and mentioned Node.js 20.9 or later. This reflects the wiki at collection time, not a verified compatibility requirement for both historical versions. The default options and bundler behavior need exact-release confirmation.

## 3. External communication and configuration

The saved narrative describes telemetry POSTs to `https://telemetry.nextjs.org/api/v1/record`, with anonymous/project/session identifiers, metadata and event fields. It gives `NEXT_TELEMETRY_DISABLED=1` or `next telemetry disable` as controls. A historical claim about a five-second timeout was not reproduced in the 15.1.0 recheck. Disabling telemetry does not establish that all possible network traffic is disabled. [Source: historical DeepWiki communication narrative]

The narrative also mentions `experimental.agentUpgrade` and `assessUpgrade`, but its destination and transmitted data were not established. Later wiki material describes opt-in feedback submission after user review. These behaviors are not proven to exist in the exact reviewed releases. OpenTelemetry is described through `instrumentation.ts` and an application-selected collector; do not confuse it with the framework's telemetry endpoint. The historical `NEXT_OTEL_FETCH_DISABLED` claim was not reproduced in one recheck, so verify it before using it as a control.

Configuration descriptions include `next.config.js`, `next.config.ts` and `.env` variants. `NEXT_PUBLIC_` values are described as being embedded in browser bundles at build time; secrets must not use that prefix. The narrative mentions `SESSION_SECRET`, `server-only` and `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY`. A claim that a generated encryption key is stored in `.rscinfo` was not reproduced and is not asserted here as fact. Actual secret values and private environment files are not part of this report.

## 4. License review

`next@16.4.6`: MIT.

Categories are screening outcomes, not legal conclusions. `unknown` includes missing metadata, unsupported identifiers and uninterpreted exceptions. A list with an unspecified relationship is conservatively reviewed as AND; an OR choice must be selected and documented.

| Package | Version | License | Category | Dependency path |
|---|---|---|---|---|
| @emnapi/runtime | 1.11.3 | MIT | permissive | next@16.4.6 → sharp@0.35.5 → @img/sharp-freebsd-wasm32@0.35.5 → @img/sharp-wasm32@0.35.5 → @emnapi/runtime@1.11.3 |
| @img/colour | 1.1.0 | MIT | permissive | next@16.4.6 → sharp@0.35.5 → @img/colour@1.1.0 |
| @img/sharp-darwin-arm64 | 0.35.5 | Apache-2.0 | permissive | next@16.4.6 → sharp@0.35.5 → @img/sharp-darwin-arm64@0.35.5 |
| @img/sharp-darwin-x64 | 0.35.5 | Apache-2.0 | permissive | next@16.4.6 → sharp@0.35.5 → @img/sharp-darwin-x64@0.35.5 |
| @img/sharp-freebsd-wasm32 | 0.35.5 | Apache-2.0 | permissive | next@16.4.6 → sharp@0.35.5 → @img/sharp-freebsd-wasm32@0.35.5 |
| @img/sharp-libvips-darwin-arm64 | 1.3.4 | LGPL-3.0-or-later | weak-copyleft | next@16.4.6 → sharp@0.35.5 → @img/sharp-libvips-darwin-arm64@1.3.4 |
| @img/sharp-libvips-darwin-x64 | 1.3.4 | LGPL-3.0-or-later | weak-copyleft | next@16.4.6 → sharp@0.35.5 → @img/sharp-libvips-darwin-x64@1.3.4 |
| @img/sharp-libvips-linux-arm | 1.3.4 | LGPL-3.0-or-later | weak-copyleft | next@16.4.6 → sharp@0.35.5 → @img/sharp-libvips-linux-arm@1.3.4 |
| @img/sharp-libvips-linux-arm64 | 1.3.4 | LGPL-3.0-or-later | weak-copyleft | next@16.4.6 → sharp@0.35.5 → @img/sharp-libvips-linux-arm64@1.3.4 |
| @img/sharp-libvips-linux-ppc64 | 1.3.4 | LGPL-3.0-or-later | weak-copyleft | next@16.4.6 → sharp@0.35.5 → @img/sharp-libvips-linux-ppc64@1.3.4 |
| @img/sharp-libvips-linux-riscv64 | 1.3.4 | LGPL-3.0-or-later | weak-copyleft | next@16.4.6 → sharp@0.35.5 → @img/sharp-libvips-linux-riscv64@1.3.4 |
| @img/sharp-libvips-linux-s390x | 1.3.4 | LGPL-3.0-or-later | weak-copyleft | next@16.4.6 → sharp@0.35.5 → @img/sharp-libvips-linux-s390x@1.3.4 |
| @img/sharp-libvips-linux-x64 | 1.3.4 | LGPL-3.0-or-later | weak-copyleft | next@16.4.6 → sharp@0.35.5 → @img/sharp-libvips-linux-x64@1.3.4 |
| @img/sharp-libvips-linuxmusl-arm64 | 1.3.4 | LGPL-3.0-or-later | weak-copyleft | next@16.4.6 → sharp@0.35.5 → @img/sharp-libvips-linuxmusl-arm64@1.3.4 |
| @img/sharp-libvips-linuxmusl-x64 | 1.3.4 | LGPL-3.0-or-later | weak-copyleft | next@16.4.6 → sharp@0.35.5 → @img/sharp-libvips-linuxmusl-x64@1.3.4 |
| @img/sharp-linux-arm | 0.35.5 | Apache-2.0 | permissive | next@16.4.6 → sharp@0.35.5 → @img/sharp-linux-arm@0.35.5 |
| @img/sharp-linux-arm64 | 0.35.5 | Apache-2.0 | permissive | next@16.4.6 → sharp@0.35.5 → @img/sharp-linux-arm64@0.35.5 |
| @img/sharp-linux-ppc64 | 0.35.5 | Apache-2.0 | permissive | next@16.4.6 → sharp@0.35.5 → @img/sharp-linux-ppc64@0.35.5 |
| @img/sharp-linux-riscv64 | 0.35.5 | Apache-2.0 | permissive | next@16.4.6 → sharp@0.35.5 → @img/sharp-linux-riscv64@0.35.5 |
| @img/sharp-linux-s390x | 0.35.5 | Apache-2.0 | permissive | next@16.4.6 → sharp@0.35.5 → @img/sharp-linux-s390x@0.35.5 |
| @img/sharp-linux-x64 | 0.35.5 | Apache-2.0 | permissive | next@16.4.6 → sharp@0.35.5 → @img/sharp-linux-x64@0.35.5 |
| @img/sharp-linuxmusl-arm64 | 0.35.5 | Apache-2.0 | permissive | next@16.4.6 → sharp@0.35.5 → @img/sharp-linuxmusl-arm64@0.35.5 |
| @img/sharp-linuxmusl-x64 | 0.35.5 | Apache-2.0 | permissive | next@16.4.6 → sharp@0.35.5 → @img/sharp-linuxmusl-x64@0.35.5 |
| @img/sharp-wasm32 | 0.35.5 | Apache-2.0 AND LGPL-3.0-or-later AND MIT | weak-copyleft | next@16.4.6 → sharp@0.35.5 → @img/sharp-freebsd-wasm32@0.35.5 → @img/sharp-wasm32@0.35.5 |
| @img/sharp-webcontainers-wasm32 | 0.35.5 | Apache-2.0 | permissive | next@16.4.6 → sharp@0.35.5 → @img/sharp-webcontainers-wasm32@0.35.5 |
| @img/sharp-win32-arm64 | 0.35.5 | Apache-2.0 AND LGPL-3.0-or-later | weak-copyleft | next@16.4.6 → sharp@0.35.5 → @img/sharp-win32-arm64@0.35.5 |
| @img/sharp-win32-ia32 | 0.35.5 | Apache-2.0 AND LGPL-3.0-or-later | weak-copyleft | next@16.4.6 → sharp@0.35.5 → @img/sharp-win32-ia32@0.35.5 |
| @img/sharp-win32-x64 | 0.35.5 | Apache-2.0 AND LGPL-3.0-or-later | weak-copyleft | next@16.4.6 → sharp@0.35.5 → @img/sharp-win32-x64@0.35.5 |
| @next/env | 16.4.6 | MIT | permissive | next@16.4.6 → @next/env@16.4.6 |
| @next/swc-darwin-arm64 | 16.4.6 | MIT | permissive | next@16.4.6 → @next/swc-darwin-arm64@16.4.6 |
| @next/swc-darwin-x64 | 16.4.6 | MIT | permissive | next@16.4.6 → @next/swc-darwin-x64@16.4.6 |
| @next/swc-linux-arm64-gnu | 16.4.6 | MIT | permissive | next@16.4.6 → @next/swc-linux-arm64-gnu@16.4.6 |
| @next/swc-linux-arm64-musl | 16.4.6 | MIT | permissive | next@16.4.6 → @next/swc-linux-arm64-musl@16.4.6 |
| @next/swc-linux-x64-gnu | 16.4.6 | MIT | permissive | next@16.4.6 → @next/swc-linux-x64-gnu@16.4.6 |
| @next/swc-linux-x64-musl | 16.4.6 | MIT | permissive | next@16.4.6 → @next/swc-linux-x64-musl@16.4.6 |
| @next/swc-win32-arm64-msvc | 16.4.6 | MIT | permissive | next@16.4.6 → @next/swc-win32-arm64-msvc@16.4.6 |
| @next/swc-win32-x64-msvc | 16.4.6 | MIT | permissive | next@16.4.6 → @next/swc-win32-x64-msvc@16.4.6 |
| @swc/helpers | 0.5.23 | Apache-2.0 | permissive | next@16.4.6 → @swc/helpers@0.5.23 |
| baseline-browser-mapping | 2.11.35 | Apache-2.0 | permissive | next@16.4.6 → baseline-browser-mapping@2.11.35 |
| caniuse-lite | 1.0.30001823 | CC-BY-4.0 | attribution | next@16.4.6 → caniuse-lite@1.0.30001823 |
| client-only | 0.0.1 | MIT | permissive | next@16.4.6 → styled-jsx@5.1.6 → client-only@0.0.1 |
| detect-libc | 2.1.2 | Apache-2.0 | permissive | next@16.4.6 → sharp@0.35.5 → detect-libc@2.1.2 |
| nanoid | 3.3.20 | MIT | permissive | next@16.4.6 → postcss@8.5.23 → nanoid@3.3.20 |
| picocolors | 1.1.1 | ISC | permissive | next@16.4.6 → postcss@8.5.23 → picocolors@1.1.1 |
| postcss | 8.5.23 | MIT | permissive | next@16.4.6 → postcss@8.5.23 |
| semver | 7.8.6 | ISC | permissive | next@16.4.6 → sharp@0.35.5 → semver@7.8.6 |
| sharp | 0.35.5 | Apache-2.0 | permissive | next@16.4.6 → sharp@0.35.5 |
| source-map-js | 1.2.2 | BSD-3-Clause | permissive | next@16.4.6 → postcss@8.5.23 → source-map-js@1.2.2 |
| styled-jsx | 5.1.6 | MIT | permissive | next@16.4.6 → styled-jsx@5.1.6 |
| tslib | 2.9.1 | 0BSD | permissive | next@16.4.6 → @swc/helpers@0.5.23 → tslib@2.9.1 |

## 5. Known vulnerabilities

No known advisories were returned in this snapshot. This is not proof of absence.

Connected aliases count as one group. Titles are source text. Missing severity is not a zero score. A list of fixed versions is not an upgrade recommendation until the affected package and branch have been matched.

## 6. Dependencies

Direct: 15 · Transitive: 35 · graph version: `16.4.6`

The role descriptions identify `@next/env` for environment loading, platform-specific `@next/swc-*` packages for native transforms, `@swc/helpers` for generated-code helpers, caniuse-lite for browser-support data, postcss for CSS processing, sharp for image optimization, and styled-jsx for scoped styling. The 15.1.0 narrative also identifies busboy for multipart request parsing and leaves the role of `@swc/counter` unverified. These are AI-generated explanations, distinct from the graph's package/version facts.

The resolved graph contains platform-specific image and compiler packages. It does not prove that all of them are installed on one operating system or distributed in a particular application bundle. Trace the actual lockfile, build and deployment artifacts before deciding which license obligations apply. Optional extras and installation conditions can change the effective dependency set.

| Parent | Child |
|---|---|
| next@16.4.6 | @next/env@16.4.6 |
| next@16.4.6 | @next/swc-darwin-arm64@16.4.6 |
| next@16.4.6 | @next/swc-darwin-x64@16.4.6 |
| next@16.4.6 | @next/swc-linux-arm64-gnu@16.4.6 |
| next@16.4.6 | @next/swc-linux-arm64-musl@16.4.6 |
| next@16.4.6 | @next/swc-linux-x64-gnu@16.4.6 |
| next@16.4.6 | @next/swc-linux-x64-musl@16.4.6 |
| next@16.4.6 | @next/swc-win32-arm64-msvc@16.4.6 |
| next@16.4.6 | @next/swc-win32-x64-msvc@16.4.6 |
| next@16.4.6 | @swc/helpers@0.5.23 |
| next@16.4.6 | baseline-browser-mapping@2.11.35 |
| next@16.4.6 | caniuse-lite@1.0.30001823 |
| next@16.4.6 | postcss@8.5.23 |
| next@16.4.6 | sharp@0.35.5 |
| next@16.4.6 | styled-jsx@5.1.6 |
| @emnapi/runtime@1.11.3 | tslib@2.9.1 |
| @img/sharp-darwin-arm64@0.35.5 | @img/sharp-libvips-darwin-arm64@1.3.4 |
| @img/sharp-darwin-x64@0.35.5 | @img/sharp-libvips-darwin-x64@1.3.4 |
| @img/sharp-freebsd-wasm32@0.35.5 | @img/sharp-wasm32@0.35.5 |
| @img/sharp-linux-arm@0.35.5 | @img/sharp-libvips-linux-arm@1.3.4 |
| @img/sharp-linux-arm64@0.35.5 | @img/sharp-libvips-linux-arm64@1.3.4 |
| @img/sharp-linux-ppc64@0.35.5 | @img/sharp-libvips-linux-ppc64@1.3.4 |
| @img/sharp-linux-riscv64@0.35.5 | @img/sharp-libvips-linux-riscv64@1.3.4 |
| @img/sharp-linux-s390x@0.35.5 | @img/sharp-libvips-linux-s390x@1.3.4 |
| @img/sharp-linux-x64@0.35.5 | @img/sharp-libvips-linux-x64@1.3.4 |
| @img/sharp-linuxmusl-arm64@0.35.5 | @img/sharp-libvips-linuxmusl-arm64@1.3.4 |
| @img/sharp-linuxmusl-x64@0.35.5 | @img/sharp-libvips-linuxmusl-x64@1.3.4 |
| @img/sharp-wasm32@0.35.5 | @emnapi/runtime@1.11.3 |
| @img/sharp-webcontainers-wasm32@0.35.5 | @img/sharp-wasm32@0.35.5 |
| @swc/helpers@0.5.23 | tslib@2.9.1 |
| postcss@8.5.23 | nanoid@3.3.20 |
| postcss@8.5.23 | picocolors@1.1.1 |
| postcss@8.5.23 | source-map-js@1.2.2 |
| sharp@0.35.5 | @img/colour@1.1.0 |
| sharp@0.35.5 | @img/sharp-darwin-arm64@0.35.5 |
| sharp@0.35.5 | @img/sharp-darwin-x64@0.35.5 |
| sharp@0.35.5 | @img/sharp-freebsd-wasm32@0.35.5 |
| sharp@0.35.5 | @img/sharp-libvips-darwin-arm64@1.3.4 |
| sharp@0.35.5 | @img/sharp-libvips-darwin-x64@1.3.4 |
| sharp@0.35.5 | @img/sharp-libvips-linux-arm@1.3.4 |
| sharp@0.35.5 | @img/sharp-libvips-linux-arm64@1.3.4 |
| sharp@0.35.5 | @img/sharp-libvips-linux-ppc64@1.3.4 |
| sharp@0.35.5 | @img/sharp-libvips-linux-riscv64@1.3.4 |
| sharp@0.35.5 | @img/sharp-libvips-linux-s390x@1.3.4 |
| sharp@0.35.5 | @img/sharp-libvips-linux-x64@1.3.4 |
| sharp@0.35.5 | @img/sharp-libvips-linuxmusl-arm64@1.3.4 |
| sharp@0.35.5 | @img/sharp-libvips-linuxmusl-x64@1.3.4 |
| sharp@0.35.5 | @img/sharp-linux-arm@0.35.5 |
| sharp@0.35.5 | @img/sharp-linux-arm64@0.35.5 |
| sharp@0.35.5 | @img/sharp-linux-ppc64@0.35.5 |
| sharp@0.35.5 | @img/sharp-linux-riscv64@0.35.5 |
| sharp@0.35.5 | @img/sharp-linux-s390x@0.35.5 |
| sharp@0.35.5 | @img/sharp-linux-x64@0.35.5 |
| sharp@0.35.5 | @img/sharp-linuxmusl-arm64@0.35.5 |
| sharp@0.35.5 | @img/sharp-linuxmusl-x64@0.35.5 |
| sharp@0.35.5 | @img/sharp-webcontainers-wasm32@0.35.5 |
| sharp@0.35.5 | @img/sharp-win32-arm64@0.35.5 |
| sharp@0.35.5 | @img/sharp-win32-ia32@0.35.5 |
| sharp@0.35.5 | @img/sharp-win32-x64@0.35.5 |
| sharp@0.35.5 | detect-libc@2.1.2 |
| sharp@0.35.5 | semver@7.8.6 |
| styled-jsx@5.1.6 | client-only@0.0.1 |

## 7. Maintenance

The saved Scorecard total is 6.2, dated 2026-08-24. Policy v3 therefore marks maintenance conditional, even though the Maintained check is 10. A strong activity score does not erase the other measured practices. Code-Review is 9 and Security-Policy is 10; the response also includes low scores for pinned dependencies, token permissions, binary artifacts and static analysis. Branch-Protection and Signed-Releases are unevaluated (-1), and the Vulnerabilities check is absent. [Source: `data.json#/get_project/scorecard`]

The historical narrative attributes the project to Vercel, describes maintainer review and stable/canary release channels, and points security reports to Vercel's private HackerOne process. It does not establish a guaranteed stable-release cadence or independently verify the current reporting process. Refer to upstream's current security policy for a real disclosure.

| Check | Score | Source details |
|---|---|---|
| Code-Review | 9 | Found 27/29 approved changesets -- score normalized to 9 |
| Maintained | 10 | 30 commit(s) and 4 issue activity found in the last 90 days -- score normalized to 10 |
| CII-Best-Practices | 0 | no effort to earn an OpenSSF best practices badge detected |
| Dangerous-Workflow | 10 | no dangerous workflow patterns detected |
| License | 10 | license file detected |
| Token-Permissions | 0 | detected GitHub workflow tokens with excessive permissions |
| Branch-Protection | -1 | internal error: error during branchesHandler.setup: internal error: githubv4.Query: Resource not accessible by integration |
| Signed-Releases | -1 | no releases found |
| Security-Policy | 10 | security policy file detected |
| Packaging | 10 | packaging workflow detected |
| Binary-Artifacts | 0 | binaries present in source code |
| Pinned-Dependencies | 4 | dependency not pinned by hash detected -- score normalized to 4 |
| Fuzzing | 10 | project is fuzzed |
| SAST | 0 | SAST tool is not run on all commits -- score normalized to 0 |

## 8. Adoption actions

1. For 15.1.0, treat known high-severity findings as blockers for the reviewed version. Match each advisory's ecosystem, affected package and branch before selecting a replacement. The existence of a fixed version does not make 15.1.0 safe.
2. Verify the actual resolved postcss and sharp versions after any framework upgrade. Re-run the review and relevant application tests; do not infer remediation solely from a framework version number or the flattened fixed-version list.
3. Inspect caniuse-lite's CC-BY-4.0 attribution conditions and the LGPL obligations of the sharp/libvips artifacts actually shipped. Policy/3 classifies CC-BY-4.0 as attribution review (conditional), rather than unknown. Check attribution, license links and change notices for the covered material.
4. For 15.1.0, inspect the exact busboy and streamsearch license files because their saved metadata arrays are empty. Empty metadata is not proof of license absence.
5. Review telemetry configuration, browser-exposed environment variables and image-processing features against the exact release and deployment. Do not rely on wiki claims that were not reproduced.
6. Record unresolved maintenance practices and obtain current evidence before production approval. Preserve this snapshot when translating or comparing versions.

## 9. Unknowns and limitations

Coverage gaps: No additional machine coverage flag. Narrative limitations below still apply.

The original report used an agent verification status of WARN. Some DeepWiki claims were not reproduced, including `.rscinfo` key storage and particular telemetry/default settings. Several other sections were not rechecked. The repository wiki can describe a newer major version, so it cannot establish version-specific runtime behavior by itself.

For 15.1.0, the old `data.json` has `deepwiki: null`; its narrative survived in the historical Markdown, but there is no corresponding saved raw wiki block to verify. Treat the explanatory paragraphs as inherited, unverified context. For 16.4.6, a saved wiki block exists, but version applicability is still unverified. In both cases the public-registry graph was not compared with a real installed application, and the original Scorecard was 85 days old at collection time.

## 10. Evidence and verification

| Claim | Source |
|---|---|
| License | data.json#/lookup_package/licenses |
| Dependencies | data.json#/get_dependencies |
| Known vulnerabilities | data.json#/advisories |
| Maintenance | data.json#/get_project/scorecard |
| DeepWiki | data.json#/deepwiki |

Verification status: **WARN**. The original JSON hash, policy calculation and bilingual numerical tables are checked. This does not freshly authenticate the old external responses or verify every wiki assertion.

SHA-256 (`data.json`): `ace41db5490e85ed6e0fd649a1d48e7aed385aa32019bbaf046a9eec17b266db`

[deps.dev](https://deps.dev/) · [OSV](https://osv.dev/) · [DeepWiki](https://deepwiki.com/vercel/next.js)

See [NOTICE](../../NOTICE.md) for source attribution and terms.
