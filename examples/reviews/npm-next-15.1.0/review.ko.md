# next 15.1.0: 오픈소스 도입 검토서

자료 수집일: 2026-11-17T00:00:00Z · npm · vercel/next.js · oss-gate.policy/3

> 과거 자료로 만든 예제입니다. 원본 스냅샷을 보존하고 정책 v3로 판정을 다시 계산했습니다. 실시간 검사 결과가 아닙니다.

**판정: 보류**

Next.js는 React 라우팅, 서버 렌더링, 서버 기능과 빌드 도구를 묶는다. 저장된 두 버전 모두 의존성 라이선스 확인이 필요하다. 15.1.0에는 패키지 자신과 의존성 그래프의 높은 심각도 취약점도 있다. 이 과거 예제는 같은 프레임워크라도 버전에 따라 결과가 달라짐을 보여 준다. 현재 시점에 오래된 릴리스를 설치하라는 권고는 아니다.

## 1. 판정과 범위

| 영역 | 판정 |
|---|---|
| 라이선스 | 보류 |
| 알려진 취약점 | 보류 |
| 의존성 | 보류 |
| 유지보수 | 조건부 |

도입 검토를 돕는 자료이며 법적 판단이나 보안 인증이 아닙니다. 공개 메타데이터는 불완전할 수 있습니다. DeepWiki 설명은 AI 생성 자료이며 검토 버전과 다를 수 있습니다.

과거 판정: `보류`. 현재 표는 동일한 저장 자료에 정책 v3를 적용한 결과다.

## 2. 이 소프트웨어는 무엇인가

과거 DeepWiki 설명에는 App Router·Pages Router, 서버 렌더링 React 앱, 통합 컴파일·빌드 도구가 있다. Turbopack, 캐싱, 부분 프리렌더링도 다루지만 저장소 위키는 요청한 패키지 버전에 고정돼 있지 않다. 특히 새 Next.js 동작에 관한 설명을 15.1.0에도 적용하면 안 된다. [출처: 과거 검토서의 설명, 존재하는 경우 `data.json#/deepwiki`]

저장소는 `packages/next`에 프레임워크, `crates`에 네이티브 코드, `turbopack`에 Turbopack 소스가 있는 pnpm 모노레포로 설명됐다. CLI 진입점에는 `next-dev.ts`, `next-build.ts`, `next-start.ts`가 있다. 요청 흐름 설명은 `router-server.ts`, `resolveRoutes`, `BaseServer`, 라우트 매칭, App/Page 모듈 또는 라우트 핸들러를 거친다. 렌더링 중 요청별 URL·헤더·쿠키를 사용한다. 발췌만으로 Edge Proxy의 최종 변환 경로 전체를 확인하지는 못했다.

컴파일 설명은 서버 액션·React Server Components 등의 Rust SWC 변환, NAPI 바인딩, 별도 WASM 빌드를 다룬다. 네이티브 패키지 선택과 일부 런타임 로딩 세부는 확인하지 못했다. 과거 시작 설명에는 `pnpm create next-app@latest my-app --yes`, `pnpm dev`, Node.js 20.9 이상이 제시됐다. 수집 당시 위키의 내용이며 두 과거 버전 모두에 검증된 호환성 조건은 아니다. 기본 선택지와 번들러 동작은 정확한 릴리스에서 확인해야 한다.

## 3. 외부 통신과 설정

저장된 설명은 `https://telemetry.nextjs.org/api/v1/record`로 익명·프로젝트·세션 식별자, 메타데이터와 이벤트 필드를 POST한다고 한다. 제어 방법으로 `NEXT_TELEMETRY_DISABLED=1` 또는 `next telemetry disable`을 제시한다. 5초 제한에 관한 과거 주장은 15.1.0 재질문에서 재현되지 않았다. 텔레메트리를 끄는 것으로 모든 네트워크 통신이 차단된다고 할 수는 없다. [출처: 과거 DeepWiki 외부 통신 설명]

`experimental.agentUpgrade`, `assessUpgrade`도 언급됐지만 목적지와 전송 데이터는 확인하지 못했다. 이후 위키에는 사용자 검토 후 선택적으로 제출하는 피드백 기능이 설명돼 있다. 이 동작들이 검토한 정확한 릴리스에 존재하는지 증명되지 않았다. OpenTelemetry는 `instrumentation.ts`와 앱이 선택한 수집기를 사용하는 것으로 설명되며, 프레임워크 텔레메트리 목적지와 구분해야 한다. `NEXT_OTEL_FETCH_DISABLED` 주장은 한 재질문에서 재현되지 않았으므로 제어 수단으로 쓰기 전에 검증한다.

설정 설명에는 `next.config.js`, `next.config.ts`, `.env` 계열이 있다. `NEXT_PUBLIC_` 값은 빌드 때 브라우저 번들에 포함되는 것으로 설명되므로 비밀에 이 접두사를 붙이면 안 된다. `SESSION_SECRET`, `server-only`, `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY`도 언급된다. 생성한 암호화 키를 `.rscinfo`에 저장한다는 주장은 재현되지 않아 여기서는 사실로 단정하지 않는다. 실제 비밀 값이나 비공개 환경 파일은 이 보고서에 포함하지 않는다.

## 4. 라이선스 검토

`next@15.1.0`: MIT.

분류는 법적 판단이 아니다. `unknown`은 자동 승인하지 않는 항목이며, 메타데이터 누락·미지원 식별자·미해석 예외를 포함한다. 여러 라이선스의 관계가 명시되지 않은 목록은 보수적으로 AND처럼 검토한다. OR 선택지는 선택·적용 근거를 기록해야 한다.

| 패키지 | 버전 | 라이선스 | Category | 의존성 경로 |
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
| busboy | 1.6.0 | 미측정 | unknown | next@15.1.0 → busboy@1.6.0 |
| caniuse-lite | 1.0.30001823 | CC-BY-4.0 | attribution | next@15.1.0 → caniuse-lite@1.0.30001823 |
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
| streamsearch | 1.1.0 | 미측정 | unknown | next@15.1.0 → busboy@1.6.0 → streamsearch@1.1.0 |
| styled-jsx | 5.1.6 | MIT | permissive | next@15.1.0 → styled-jsx@5.1.6 |
| tslib | 2.9.1 | 0BSD | permissive | next@15.1.0 → @swc/helpers@0.5.15 → tslib@2.9.1 |

## 5. 알려진 취약점

| ID | 점수 | Aliases | 출처 상세 |
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

별칭이 연결된 권고는 한 묶음으로 집계한다. 제목은 출처 원문이다. 점수 미상은 0점으로 바꾸지 않는다. 수정 버전 목록은 패키지·버전 분기를 대조하기 전에는 업그레이드 권고가 아니다.

## 6. 의존성

직접 의존성: 16 · 간접 의존성: 34 · graph version: `15.1.0`

역할 설명은 `@next/env`를 환경 로딩, 플랫폼별 `@next/swc-*`를 네이티브 변환, `@swc/helpers`를 변환 코드 보조 함수, caniuse-lite를 브라우저 지원 데이터, postcss를 CSS 처리, sharp를 이미지 최적화, styled-jsx를 범위 지정 스타일로 제시한다. 15.1.0 설명에는 multipart 요청 파싱용 busboy도 있고 `@swc/counter` 역할은 미확인이다. 이는 AI 생성 설명이며 그래프의 패키지·버전 사실과 구분한다.

해석된 그래프에는 플랫폼별 이미지·컴파일러 패키지가 있다. 모든 패키지가 하나의 운영체제에 설치되거나 특정 앱 번들로 배포된다는 증거는 아니다. 실제 lockfile, 빌드와 배포 산출물을 추적한 뒤 적용되는 라이선스 의무를 판단해야 한다. 선택적 구성과 설치 조건에 따라 실제 의존성은 달라질 수 있다.

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

## 7. 유지보수

저장된 Scorecard 총점은 6.2, 기준일은 2026-08-24다. 정책 v3는 Maintained 체크가 10이어도 유지보수를 조건부로 판정한다. 활발한 활동만으로 다른 측정 항목을 상쇄하지 않는다. Code-Review 9, Security-Policy 10이며, 의존성 고정·토큰 권한·바이너리 산출물·정적 분석에는 낮은 점수도 있다. Branch-Protection과 Signed-Releases는 미평가(-1)이고 Vulnerabilities 체크는 없다. [출처: `data.json#/get_project/scorecard`]

과거 설명은 Vercel의 프로젝트, 유지관리자 리뷰, stable·canary 릴리스 채널, Vercel HackerOne을 통한 비공개 보안 신고를 제시한다. 고정된 stable 릴리스 주기나 현재 신고 절차를 독립적으로 검증한 것은 아니다. 실제 신고에는 upstream의 최신 보안 정책을 따른다.

| Check | 점수 | 출처 상세 |
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

## 8. 도입 조치

1. 15.1.0의 알려진 높은 심각도 취약점은 해당 버전의 도입 차단 항목으로 본다. 대체 버전을 고르기 전에 권고별 생태계·영향 패키지·버전 분기를 대조한다. 수정 버전이 존재해도 15.1.0 자체가 안전해지지는 않는다.
2. 프레임워크를 올린 뒤 실제 해석된 postcss·sharp 버전을 확인한다. 검토와 관련 앱 테스트를 다시 실행한다. 프레임워크 버전이나 평탄화된 수정 버전 목록만으로 해결됐다고 추정하지 않는다.
3. 실제 배포되는 sharp/libvips 산출물의 LGPL 의무와 caniuse-lite CC-BY-4.0의 출처 표시 조건을 검토한다. 정책/3은 CC-BY-4.0을 unknown 대신 출처 표시 검토가 필요한 조건부로 분류한다. 해당 자료의 출처·라이선스 링크·변경 고지를 확인해야 한다.
4. 15.1.0의 busboy·streamsearch는 저장된 메타데이터 배열이 비어 있으므로 정확한 버전의 라이선스 파일을 확인한다. 빈 메타데이터가 라이선스 부재의 증거는 아니다.
5. 정확한 릴리스·배포 환경에서 텔레메트리 설정, 브라우저 노출 환경 변수, 이미지 처리 기능을 점검한다. 재현되지 않은 위키 설명에 의존하지 않는다.
6. 미확인 유지보수 관행을 기록하고 운영 승인 전에 최신 자료를 확보한다. 번역하거나 버전을 비교할 때 이 스냅샷은 보존한다.

## 9. 확인하지 못한 것

미확인 범위: 자동 점검상 추가 플래그 없음. 아래 서술의 한계는 별도로 남아 있다.

기존 에이전트 검토 결과는 WARN이다. `.rscinfo` 키 저장, 일부 텔레메트리·기본 설정 등 DeepWiki 주장이 재현되지 않았다. 다른 일부 절도 다시 확인하지 않았다. 저장소 위키가 새 주요 버전을 설명할 수 있으므로 이것만으로 특정 버전의 실행 동작을 확정할 수 없다.

15.1.0의 기존 `data.json`에는 `deepwiki: null`이 들어 있다. 설명은 과거 마크다운에 남았지만 대응하는 원본 위키 블록을 저장하지 못해 확인할 수 없다. 설명 문단은 과거에서 이어받은 미검증 참고 자료로 취급한다. 16.4.6에는 저장된 위키 블록이 있지만 버전 적용 여부는 여전히 미확인이다. 두 버전 모두 공개 레지스트리 그래프를 실제 설치 앱과 대조하지 않았고, 기존 Scorecard는 수집 당시 85일 전 자료였다.

## 10. 근거와 검증

| 주장 | 출처 |
|---|---|
| 라이선스 | data.json#/lookup_package/licenses |
| 의존성 | data.json#/get_dependencies |
| 알려진 취약점 | data.json#/advisories |
| 유지보수 | data.json#/get_project/scorecard |
| DeepWiki | Unavailable in the historical JSON |

검증 상태: **WARN**. 원본 JSON 해시와 정책 재계산·언어별 수치 표를 확인했다. 과거 외부 응답의 진위와 위키 서술 전체를 새로 확인한 것은 아니다.

SHA-256 (`data.json`): `dfabfde8c552992dac2f736f4223f55cd06a4b5c7c4b24817e474eeaa627d873`

[deps.dev](https://deps.dev/) · [OSV](https://osv.dev/) · [DeepWiki](https://deepwiki.com/vercel/next.js)

출처·이용 조건은 [NOTICE](../../NOTICE.md)를 참고한다.
