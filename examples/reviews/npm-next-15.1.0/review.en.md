# next 15.1.0: Open-source adoption review

Snapshot date: 2026-11-17T00:00:00Z · npm · vercel/next.js · oss-gate.policy/2

> Historical example. The source snapshot is preserved; the verdict shown here is reassessed using policy v2. This is not a live scan.

**Verdict: Hold**

Next.js combines React routing, server rendering, server features and build tooling. Both saved versions require adoption review because of dependency-license questions. Version 15.1.0 additionally has known high-severity vulnerabilities in the package and its dependency graph. These dated examples show how the same framework can present different findings by version; neither report is a recommendation to install an old release today.

## 1. Decision and scope

| Area | Verdict |
|---|---|
| License | Hold |
| Known vulnerabilities | Hold |
| Dependencies | Hold |
| Maintenance | Conditional |

A screening aid, not a legal opinion or security certification. Public metadata can be incomplete. DeepWiki narratives are AI-generated and may not describe the reviewed version.

Historical verdict: `Hold`. The table above applies policy v2 to the same saved evidence.

## 2. What the software does

The historical DeepWiki narrative describes App Router and Pages Router, server-rendered React applications and integrated compilation/build tooling. It discusses Turbopack, caching and partial prerendering, but the repository wiki is not bound to the requested package version. In particular, descriptions of newer Next.js behavior must not be assumed to apply to 15.1.0. [Source: historical review narrative; saved `data.json#/deepwiki` where available]

The repository is described as a pnpm monorepo with the framework in `packages/next`, native code in `crates` and Turbopack sources in `turbopack`. CLI entry points include `next-dev.ts`, `next-build.ts` and `next-start.ts`. The request-flow explanation goes through `router-server.ts`, `resolveRoutes`, `BaseServer`, route matching and an App/Page module or route handler. Request-scoped URL, header and cookie data are used during rendering. The full Edge Proxy conversion path was not established by the excerpts.

The compilation explanation describes Rust SWC transforms, including server actions and React Server Components, with NAPI bindings and a separate WASM build. Native package selection and some runtime loading details were not confirmed. The original getting-started narrative gave `pnpm create next-app@latest my-app --yes`, followed by `pnpm dev`, and mentioned Node.js 20.9 or later. This reflects the wiki at collection time, not a verified compatibility requirement for both historical versions. The default options and bundler behavior need exact-release confirmation.

## 3. External communication and configuration

The saved narrative describes telemetry POSTs to `https://telemetry.nextjs.org/api/v1/record`, with anonymous/project/session identifiers, metadata and event fields. It gives `NEXT_TELEMETRY_DISABLED=1` or `next telemetry disable` as controls. A historical claim about a five-second timeout was not reproduced in the 15.1.0 recheck. Disabling telemetry does not establish that all possible network traffic is disabled. [Source: historical DeepWiki communication narrative]

The narrative also mentions `experimental.agentUpgrade` and `assessUpgrade`, but its destination and transmitted data were not established. Later wiki material describes opt-in feedback submission after user review. These behaviors are not proven to exist in the exact reviewed releases. OpenTelemetry is described through `instrumentation.ts` and an application-selected collector; do not confuse it with the framework's telemetry endpoint. The historical `NEXT_OTEL_FETCH_DISABLED` claim was not reproduced in one recheck, so verify it before using it as a control.

Configuration descriptions include `next.config.js`, `next.config.ts` and `.env` variants. `NEXT_PUBLIC_` values are described as being embedded in browser bundles at build time; secrets must not use that prefix. The narrative mentions `SESSION_SECRET`, `server-only` and `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY`. A claim that a generated encryption key is stored in `.rscinfo` was not reproduced and is not asserted here as fact. Actual secret values and private environment files are not part of this report.

## 4. License review

`next@15.1.0`: MIT.

Categories are screening outcomes, not legal conclusions. `unknown` includes missing metadata, unsupported identifiers and uninterpreted exceptions. A list with an unspecified relationship is conservatively reviewed as AND; an OR choice must be selected and documented.

| Package | Version | License | Category | Dependency path |
|---|---|---|---|---|
| @emnapi/runtime | 1.11.3 | MIT | permissive | next@15.1.0 → sharp@0.33.5 → @img/sharp-wasm32@0.33.5 → @emnapi/runtime@1.11.3 |
| @img/sharp-darwin-arm64 | 0.33.5 | Apache-2.0 | permissive | next@15.1.0 → sharp@0.33.5 → @img/sharp-darwin-arm64@0.33.5 |
| @img/sharp-darwin-x64 | 0.33.5 | Apache-2.0 | permissive | next@15.1.0 → sharp@0.33.5 → @img/sharp-darwin-x64@0.33.5 |
| @img/sharp-libvips-darwin-arm64 | 1.0.4 | LGPL-3.0-or-later | weak-copyleft | next@15.1.0 → sharp@0.33.5 → @img/sharp-libvips-darwin-arm64@1.0.4 |
| @img/sharp-libvips-darwin-x64 | 1.0.4 | LGPL-3.0-or-later | weak-copyleft | next@15.1.0 → sharp@0.33.5 → @img/sharp-libvips-darwin-x64@1.0.4 |
| @img/sharp-libvips-linux-arm | 1.0.5 | LGPL-3.0-or-later | weak-copyleft | next@15.1.0 → sharp@0.33.5 → @img/sharp-libvips-linux-arm@1.0.5 |
| @img/sharp-libvips-linux-arm64 | 1.0.4 | LGPL-3.0-or-later | weak-copyleft | next@15.1.0 → sharp@0.33.5 → @img/sharp-libvips-linux-arm64@1.0.4 |
| @img/sharp-libvips-linux-s390x | 1.0.4 | LGPL-3.0-or-later | weak-copyleft | next@15.1.0 → sharp@0.33.5 → @img/sharp-libvips-linux-s390x@1.0.4 |
| @img/sharp-libvips-linux-x64 | 1.0.4 | LGPL-3.0-or-later | weak-copyleft | next@15.1.0 → sharp@0.33.5 → @img/sharp-libvips-linux-x64@1.0.4 |
| @img/sharp-libvips-linuxmusl-arm64 | 1.0.4 | LGPL-3.0-or-later | weak-copyleft | next@15.1.0 → sharp@0.33.5 → @img/sharp-libvips-linuxmusl-arm64@1.0.4 |
| @img/sharp-libvips-linuxmusl-x64 | 1.0.4 | LGPL-3.0-or-later | weak-copyleft | next@15.1.0 → sharp@0.33.5 → @img/sharp-libvips-linuxmusl-x64@1.0.4 |
| @img/sharp-linux-arm | 0.33.5 | Apache-2.0 | permissive | next@15.1.0 → sharp@0.33.5 → @img/sharp-linux-arm@0.33.5 |
| @img/sharp-linux-arm64 | 0.33.5 | Apache-2.0 | permissive | next@15.1.0 → sharp@0.33.5 → @img/sharp-linux-arm64@0.33.5 |
| @img/sharp-linux-s390x | 0.33.5 | Apache-2.0 | permissive | next@15.1.0 → sharp@0.33.5 → @img/sharp-linux-s390x@0.33.5 |
| @img/sharp-linux-x64 | 0.33.5 | Apache-2.0 | permissive | next@15.1.0 → sharp@0.33.5 → @img/sharp-linux-x64@0.33.5 |
| @img/sharp-linuxmusl-arm64 | 0.33.5 | Apache-2.0 | permissive | next@15.1.0 → sharp@0.33.5 → @img/sharp-linuxmusl-arm64@0.33.5 |
| @img/sharp-linuxmusl-x64 | 0.33.5 | Apache-2.0 | permissive | next@15.1.0 → sharp@0.33.5 → @img/sharp-linuxmusl-x64@0.33.5 |
| @img/sharp-wasm32 | 0.33.5 | Apache-2.0 AND LGPL-3.0-or-later AND MIT | weak-copyleft | next@15.1.0 → sharp@0.33.5 → @img/sharp-wasm32@0.33.5 |
| @img/sharp-win32-ia32 | 0.33.5 | Apache-2.0 AND LGPL-3.0-or-later | weak-copyleft | next@15.1.0 → sharp@0.33.5 → @img/sharp-win32-ia32@0.33.5 |
| @img/sharp-win32-x64 | 0.33.5 | Apache-2.0 AND LGPL-3.0-or-later | weak-copyleft | next@15.1.0 → sharp@0.33.5 → @img/sharp-win32-x64@0.33.5 |
| @next/env | 15.1.0 | MIT | permissive | next@15.1.0 → @next/env@15.1.0 |
| @next/swc-darwin-arm64 | 15.1.0 | MIT | permissive | next@15.1.0 → @next/swc-darwin-arm64@15.1.0 |
| @next/swc-darwin-x64 | 15.1.0 | MIT | permissive | next@15.1.0 → @next/swc-darwin-x64@15.1.0 |
| @next/swc-linux-arm64-gnu | 15.1.0 | MIT | permissive | next@15.1.0 → @next/swc-linux-arm64-gnu@15.1.0 |
| @next/swc-linux-arm64-musl | 15.1.0 | MIT | permissive | next@15.1.0 → @next/swc-linux-arm64-musl@15.1.0 |
| @next/swc-linux-x64-gnu | 15.1.0 | MIT | permissive | next@15.1.0 → @next/swc-linux-x64-gnu@15.1.0 |
| @next/swc-linux-x64-musl | 15.1.0 | MIT | permissive | next@15.1.0 → @next/swc-linux-x64-musl@15.1.0 |
| @next/swc-win32-arm64-msvc | 15.1.0 | MIT | permissive | next@15.1.0 → @next/swc-win32-arm64-msvc@15.1.0 |
| @next/swc-win32-x64-msvc | 15.1.0 | MIT | permissive | next@15.1.0 → @next/swc-win32-x64-msvc@15.1.0 |
| @swc/counter | 0.1.3 | Apache-2.0 | permissive | next@15.1.0 → @swc/counter@0.1.3 |
| @swc/helpers | 0.5.15 | Apache-2.0 | permissive | next@15.1.0 → @swc/helpers@0.5.15 |
| busboy | 1.6.0 | Not measured | unknown | next@15.1.0 → busboy@1.6.0 |
| caniuse-lite | 1.0.30001823 | CC-BY-4.0 | unknown | next@15.1.0 → caniuse-lite@1.0.30001823 |
| client-only | 0.0.1 | MIT | permissive | next@15.1.0 → styled-jsx@5.1.6 → client-only@0.0.1 |
| color | 4.2.3 | MIT | permissive | next@15.1.0 → sharp@0.33.5 → color@4.2.3 |
| color-convert | 2.0.1 | MIT | permissive | next@15.1.0 → sharp@0.33.5 → color@4.2.3 → color-convert@2.0.1 |
| color-name | 1.1.4 | MIT | permissive | next@15.1.0 → sharp@0.33.5 → color@4.2.3 → color-convert@2.0.1 → color-name@1.1.4 |
| color-string | 1.9.1 | MIT | permissive | next@15.1.0 → sharp@0.33.5 → color@4.2.3 → color-string@1.9.1 |
| detect-libc | 2.1.2 | Apache-2.0 | permissive | next@15.1.0 → sharp@0.33.5 → detect-libc@2.1.2 |
| is-arrayish | 0.3.4 | MIT | permissive | next@15.1.0 → sharp@0.33.5 → color@4.2.3 → color-string@1.9.1 → simple-swizzle@0.2.4 → is-arrayish@0.3.4 |
| nanoid | 3.3.20 | MIT | permissive | next@15.1.0 → postcss@8.4.31 → nanoid@3.3.20 |
| picocolors | 1.1.1 | ISC | permissive | next@15.1.0 → postcss@8.4.31 → picocolors@1.1.1 |
| postcss | 8.4.31 | MIT | permissive | next@15.1.0 → postcss@8.4.31 |
| semver | 7.8.6 | ISC | permissive | next@15.1.0 → sharp@0.33.5 → semver@7.8.6 |
| sharp | 0.33.5 | Apache-2.0 | permissive | next@15.1.0 → sharp@0.33.5 |
| simple-swizzle | 0.2.4 | MIT | permissive | next@15.1.0 → sharp@0.33.5 → color@4.2.3 → color-string@1.9.1 → simple-swizzle@0.2.4 |
| source-map-js | 1.2.2 | BSD-3-Clause | permissive | next@15.1.0 → postcss@8.4.31 → source-map-js@1.2.2 |
| streamsearch | 1.1.0 | Not measured | unknown | next@15.1.0 → busboy@1.6.0 → streamsearch@1.1.0 |
| styled-jsx | 5.1.6 | MIT | permissive | next@15.1.0 → styled-jsx@5.1.6 |
| tslib | 2.9.1 | 0BSD | permissive | next@15.1.0 → @swc/helpers@0.5.15 → tslib@2.9.1 |

## 5. Known vulnerabilities

| ID | Score | Aliases | Source details |
|---|---|---|---|
| GHSA-9qr9-h5gf-34mp | 10 | GHSA-9qr9-h5gf-34mp | Next.js is vulnerable to RCE in React flight protocol |
| GHSA-f82v-jwr5-mffw | 9.1 | CVE-2025-29927, GHSA-f82v-jwr5-mffw | Authorization Bypass in Next.js Middleware |
| GHSA-p293-qw3h-jr36 | 9 | CVE-2026-75604, GHSA-p293-qw3h-jr36 | Next.js: Unauthenticated Remote Code Execution on windows-hosted servers |
| GHSA-c4j6-fc7j-m34r | 8.6 | CVE-2026-44578, GHSA-c4j6-fc7j-m34r | Next.js vulnerable to server-side request forgery in applications using WebSocket upgrades |
| GHSA-36qx-fr4f-26g5 | 7.5 | CVE-2026-44573, GHSA-36qx-fr4f-26g5 | Next.js has a Middleware / Proxy bypass in Pages Router applications using i18n |
| GHSA-67rr-84xm-4c7r | 7.5 | CVE-2025-49826, GHSA-67rr-84xm-4c7r | Next.JS vulnerability can lead to DoS via cache poisoning  |
| GHSA-6g55-p6wh-862q | 7.5 | CVE-2026-45623, GHSA-6g55-p6wh-862q | PostCSS: Arbitrary file read and information disclosure via attacker-controlled sourceMappingURL in CSS comments |
| GHSA-8h8q-6873-q5fj | 7.5 | GHSA-8h8q-6873-q5fj | Next.js Vulnerable to Denial of Service with Server Components |
| GHSA-mg66-mrh9-m8jx | 7.5 | CVE-2026-44579, GHSA-mg66-mrh9-m8jx | Next.js vulnerable to Denial of Service via connection exhaustion in applications using Cache Components |
| GHSA-q4gf-8mx6-v5v3 | 7.5 | GHSA-q4gf-8mx6-v5v3 | Next.js has a Denial of Service with Server Components |
| GHSA-r28c-9q8g-f849 | 7.5 | CVE-2026-73646, GHSA-r28c-9q8g-f849 | PostCSS: Path Traversal in Previous Source Map Auto-Loading (sourceMappingURL) leads to Arbitrary .map File Disclosure |
| GHSA-4342-x723-ch2f | 6.5 | CVE-2025-57822, GHSA-4342-x723-ch2f | Next.js Improper Middleware Redirect Handling Leads to SSRF |
| GHSA-g5qg-72qw-gw5v | 6.2 | CVE-2025-57752, GHSA-g5qg-72qw-gw5v | Next.js Affected by Cache Key Confusion for Image Optimization API Routes |
| GHSA-gx5p-jg67-6x7h | 6.1 | CVE-2026-44580, GHSA-gx5p-jg67-6x7h | Next.js has cross-site scripting in beforeInteractive scripts with untrusted input |
| GHSA-qx2v-qp2m-jg93 | 6.1 | CVE-2026-41305, GHSA-qx2v-qp2m-jg93 | PostCSS has XSS via Unescaped </style> in its CSS Stringify Output |
| GHSA-9g9p-9gw9-jx7f | 5.9 | CVE-2025-59471, GHSA-9g9p-9gw9-jx7f | Next.js self-hosted applications vulnerable to DoS via Image Optimizer remotePatterns configuration |
| GHSA-h64f-5h5j-jqjh | 5.9 | CVE-2026-44577, GHSA-h64f-5h5j-jqjh | Next.js has a Denial of Service in the Image Optimization API |
| GHSA-wfc6-r584-vfw7 | 5.4 | CVE-2026-44576, GHSA-wfc6-r584-vfw7 | Next.js vulnerable to cache poisoning in React Server Component responses |
| GHSA-4jqv-mc3x-m676 | 5.3 | CVE-2026-94543, GHSA-4jqv-mc3x-m676 | Next.js has cache poisoning of SSG and ISR pages in self-hosted applications |
| GHSA-7m27-7ghc-44w9 | 5.3 | CVE-2024-56332, GHSA-7m27-7ghc-44w9 | Next.js Allows a Denial of Service (DoS) with Server Actions |
| GHSA-mcj8-r9mp-w47p | 4.8 | CVE-2026-94484, GHSA-mcj8-r9mp-w47p | Next.js has cache poisoning in SSG/ISR rendering that leads to cross-user content substitution and persistent denial of service |
| GHSA-ffhc-5mcf-pf4q | 4.7 | CVE-2026-44581, GHSA-ffhc-5mcf-pf4q | Next.js vulnerable to cross-site scripting in App Router applications using CSP nonces |
| GHSA-xv57-4mr9-wg8v | 4.3 | CVE-2025-55173, GHSA-xv57-4mr9-wg8v | Next.js Content Injection Vulnerability for Image Optimization |
| GHSA-3g8h-86w9-wvmq | 3.7 | CVE-2026-44572, GHSA-3g8h-86w9-wvmq | Next.js's Middleware / Proxy redirects can be cache-poisoned |
| GHSA-qpjv-v59x-3qc4 | 3.7 | CVE-2025-32421, GHSA-qpjv-v59x-3qc4 | Next.js Race Condition to Cache Poisoning |
| GHSA-vfv6-92ff-j949 | 3.7 | CVE-2026-44582, GHSA-vfv6-92ff-j949 | Next.js vulnerable to cache poisoning via collisions in React Server Component cache-busting |
| GHSA-2464-fhr4-w9xw | 0 | GHSA-2464-fhr4-w9xw | Next.js: Unauthenticated Remote Code Execution in Image Optimization API when SVG files are used |
| GHSA-2xp9-vwfh-vxw4 | 0 | GHSA-2xp9-vwfh-vxw4 | Next.js: Unauthenticated Remote Code Execution in Image Optimization API when AVIF files are used |
| GHSA-3x4c-7xq6-9pq8 | 0 | CVE-2026-27980, GHSA-3x4c-7xq6-9pq8 | Next.js: Unbounded next/image disk cache growth can exhaust storage |
| GHSA-4633-3j49-mh5q | 0 | CVE-2026-64647, GHSA-4633-3j49-mh5q | Next.js: Cache confusion of response bodies for requests with bodies containing invalid UTF-8 byte sequences |
| GHSA-4c39-4ccg-62r3 | 0 | CVE-2026-64646, GHSA-4c39-4ccg-62r3 | Next.js: Unbounded Server Action payload in Edge runtime |
| GHSA-68g3-v927-f742 | 0 | CVE-2026-64648, GHSA-68g3-v927-f742 | Next.js: Cache confusion of response bodies for requests with bodies |
| GHSA-89xv-2m56-2m9x | 0 | CVE-2026-64649, GHSA-89xv-2m56-2m9x | Next.js: Server-Side Request Forgery in Server Actions on custom servers |
| GHSA-955p-x3mx-jcvp | 0 | CVE-2026-64643, GHSA-955p-x3mx-jcvp | Next.js: Unauthenticated disclosure of internal Server Function endpoints |
| GHSA-f88m-g3jw-g9cj | 0 | CVE-2026-114113, GHSA-f88m-g3jw-g9cj | sharp inherited vulnerabilities in libvips: CVE-2026-33327, CVE-2026-33328, CVE-2026-35590, CVE-2026-35591 |
| GHSA-fxqj-rqcc-2cmp | 0 | CVE-2026-69153, GHSA-fxqj-rqcc-2cmp | PostCSS: incomplete fix of GHSA-6g55-p6wh-862q — attacker-controlled sourceMappingURL reads arbitrary .map files when `from` is unset |
| GHSA-ggv3-7p47-pfv8 | 0 | CVE-2026-29057, GHSA-ggv3-7p47-pfv8 | Next.js: HTTP request smuggling in rewrites |
| GHSA-m99w-x7hq-7vfj | 0 | CVE-2026-64641, GHSA-m99w-x7hq-7vfj | Next.js: Denial of Service in App Router using Server Actions |
| GHSA-p3m5-59mp-jv5r | 0 | CVE-2026-94482, GHSA-p3m5-59mp-jv5r | Next.js: Denial of Service in App Router using Server Actions |
| GHSA-p9j2-gv94-2wf4 | 0 | CVE-2026-64645, GHSA-p9j2-gv94-2wf4 | Next.js: Server-Side Request Forgery in rewrites via attacker-controlled destination hostname |
| GHSA-rgj7-g3m4-5g8c | 0 | CVE-2026-114112, GHSA-rgj7-g3m4-5g8c | sharp: Vulnerabilities in libheif: GHSA-g89c-p67h-r497 and GHSA-2jg2-4ch7-h545 |
| GHSA-wq5f-xc86-pv6w | 0 | CVE-2026-114111, GHSA-wq5f-xc86-pv6w | sharp : Vulnerability in librsvg dependency CVE-2026-96889 |

Connected aliases count as one group. Titles are source text. Missing severity is not a zero score. A list of fixed versions is not an upgrade recommendation until the affected package and branch have been matched.

## 6. Dependencies

Direct: 16 · Transitive: 34 · graph version: `15.1.0`

The role descriptions identify `@next/env` for environment loading, platform-specific `@next/swc-*` packages for native transforms, `@swc/helpers` for generated-code helpers, caniuse-lite for browser-support data, postcss for CSS processing, sharp for image optimization, and styled-jsx for scoped styling. The 15.1.0 narrative also identifies busboy for multipart request parsing and leaves the role of `@swc/counter` unverified. These are AI-generated explanations, distinct from the graph's package/version facts.

The resolved graph contains platform-specific image and compiler packages. It does not prove that all of them are installed on one operating system or distributed in a particular application bundle. Trace the actual lockfile, build and deployment artifacts before deciding which license obligations apply. Optional extras and installation conditions can change the effective dependency set.

| Parent | Child |
|---|---|
| next@15.1.0 | @next/env@15.1.0 |
| next@15.1.0 | @next/swc-darwin-arm64@15.1.0 |
| next@15.1.0 | @next/swc-darwin-x64@15.1.0 |
| next@15.1.0 | @next/swc-linux-arm64-gnu@15.1.0 |
| next@15.1.0 | @next/swc-linux-arm64-musl@15.1.0 |
| next@15.1.0 | @next/swc-linux-x64-gnu@15.1.0 |
| next@15.1.0 | @next/swc-linux-x64-musl@15.1.0 |
| next@15.1.0 | @next/swc-win32-arm64-msvc@15.1.0 |
| next@15.1.0 | @next/swc-win32-x64-msvc@15.1.0 |
| next@15.1.0 | @swc/counter@0.1.3 |
| next@15.1.0 | @swc/helpers@0.5.15 |
| next@15.1.0 | busboy@1.6.0 |
| next@15.1.0 | caniuse-lite@1.0.30001823 |
| next@15.1.0 | postcss@8.4.31 |
| next@15.1.0 | sharp@0.33.5 |
| next@15.1.0 | styled-jsx@5.1.6 |
| @emnapi/runtime@1.11.3 | tslib@2.9.1 |
| @img/sharp-darwin-arm64@0.33.5 | @img/sharp-libvips-darwin-arm64@1.0.4 |
| @img/sharp-darwin-x64@0.33.5 | @img/sharp-libvips-darwin-x64@1.0.4 |
| @img/sharp-linux-arm@0.33.5 | @img/sharp-libvips-linux-arm@1.0.5 |
| @img/sharp-linux-arm64@0.33.5 | @img/sharp-libvips-linux-arm64@1.0.4 |
| @img/sharp-linux-s390x@0.33.5 | @img/sharp-libvips-linux-s390x@1.0.4 |
| @img/sharp-linux-x64@0.33.5 | @img/sharp-libvips-linux-x64@1.0.4 |
| @img/sharp-linuxmusl-arm64@0.33.5 | @img/sharp-libvips-linuxmusl-arm64@1.0.4 |
| @img/sharp-linuxmusl-x64@0.33.5 | @img/sharp-libvips-linuxmusl-x64@1.0.4 |
| @img/sharp-wasm32@0.33.5 | @emnapi/runtime@1.11.3 |
| @swc/helpers@0.5.15 | tslib@2.9.1 |
| busboy@1.6.0 | streamsearch@1.1.0 |
| color@4.2.3 | color-convert@2.0.1 |
| color@4.2.3 | color-string@1.9.1 |
| color-convert@2.0.1 | color-name@1.1.4 |
| color-string@1.9.1 | color-name@1.1.4 |
| color-string@1.9.1 | simple-swizzle@0.2.4 |
| postcss@8.4.31 | nanoid@3.3.20 |
| postcss@8.4.31 | picocolors@1.1.1 |
| postcss@8.4.31 | source-map-js@1.2.2 |
| sharp@0.33.5 | @img/sharp-darwin-arm64@0.33.5 |
| sharp@0.33.5 | @img/sharp-darwin-x64@0.33.5 |
| sharp@0.33.5 | @img/sharp-libvips-darwin-arm64@1.0.4 |
| sharp@0.33.5 | @img/sharp-libvips-darwin-x64@1.0.4 |
| sharp@0.33.5 | @img/sharp-libvips-linux-arm@1.0.5 |
| sharp@0.33.5 | @img/sharp-libvips-linux-arm64@1.0.4 |
| sharp@0.33.5 | @img/sharp-libvips-linux-s390x@1.0.4 |
| sharp@0.33.5 | @img/sharp-libvips-linux-x64@1.0.4 |
| sharp@0.33.5 | @img/sharp-libvips-linuxmusl-arm64@1.0.4 |
| sharp@0.33.5 | @img/sharp-libvips-linuxmusl-x64@1.0.4 |
| sharp@0.33.5 | @img/sharp-linux-arm@0.33.5 |
| sharp@0.33.5 | @img/sharp-linux-arm64@0.33.5 |
| sharp@0.33.5 | @img/sharp-linux-s390x@0.33.5 |
| sharp@0.33.5 | @img/sharp-linux-x64@0.33.5 |
| sharp@0.33.5 | @img/sharp-linuxmusl-arm64@0.33.5 |
| sharp@0.33.5 | @img/sharp-linuxmusl-x64@0.33.5 |
| sharp@0.33.5 | @img/sharp-wasm32@0.33.5 |
| sharp@0.33.5 | @img/sharp-win32-ia32@0.33.5 |
| sharp@0.33.5 | @img/sharp-win32-x64@0.33.5 |
| sharp@0.33.5 | color@4.2.3 |
| sharp@0.33.5 | detect-libc@2.1.2 |
| sharp@0.33.5 | semver@7.8.6 |
| simple-swizzle@0.2.4 | is-arrayish@0.3.4 |
| styled-jsx@5.1.6 | client-only@0.0.1 |

## 7. Maintenance

The saved Scorecard total is 6.2, dated 2026-08-24. Policy v2 therefore marks maintenance conditional, even though the Maintained check is 10. A strong activity score does not erase the other measured practices. Code-Review is 9 and Security-Policy is 10; the response also includes low scores for pinned dependencies, token permissions, binary artifacts and static analysis. Branch-Protection and Signed-Releases are unevaluated (-1), and the Vulnerabilities check is absent. [Source: `data.json#/get_project/scorecard`]

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
3. Inspect caniuse-lite's CC-BY-4.0 attribution conditions and the LGPL obligations of the sharp/libvips artifacts actually shipped. CC-BY-4.0 is a recognized data license; its `unknown` screening category means this policy does not automatically approve it, not that the package has no license.
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
| DeepWiki | Unavailable in the historical JSON |

Verification status: **WARN**. The original JSON hash, policy calculation and bilingual numerical tables are checked. This does not freshly authenticate the old external responses or verify every wiki assertion.

SHA-256 (`data.json`): `dfabfde8c552992dac2f736f4223f55cd06a4b5c7c4b24817e474eeaa627d873`

[deps.dev](https://deps.dev/) · [OSV](https://osv.dev/) · [DeepWiki](https://deepwiki.com/vercel/next.js)

See [NOTICE](../../NOTICE.md) for source attribution and terms.
