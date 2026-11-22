<!-- summary -->
Next.js는 React 라우팅, 서버 렌더링, 서버 기능과 빌드 도구를 묶는다. 저장된 두 버전 모두 의존성 라이선스 확인이 필요하다. 15.1.0에는 패키지 자신과 의존성 그래프의 높은 심각도 취약점도 있다. 이 과거 예제는 같은 프레임워크라도 버전에 따라 결과가 달라짐을 보여 준다. 현재 시점에 오래된 릴리스를 설치하라는 권고는 아니다.
<!-- overview -->
과거 DeepWiki 설명에는 App Router·Pages Router, 서버 렌더링 React 앱, 통합 컴파일·빌드 도구가 있다. Turbopack, 캐싱, 부분 프리렌더링도 다루지만 저장소 위키는 요청한 패키지 버전에 고정돼 있지 않다. 특히 새 Next.js 동작에 관한 설명을 15.1.0에도 적용하면 안 된다. [출처: 과거 검토서의 설명, 존재하는 경우 `data.json#/deepwiki`]

저장소는 `packages/next`에 프레임워크, `crates`에 네이티브 코드, `turbopack`에 Turbopack 소스가 있는 pnpm 모노레포로 설명됐다. CLI 진입점에는 `next-dev.ts`, `next-build.ts`, `next-start.ts`가 있다. 요청 흐름 설명은 `router-server.ts`, `resolveRoutes`, `BaseServer`, 라우트 매칭, App/Page 모듈 또는 라우트 핸들러를 거친다. 렌더링 중 요청별 URL·헤더·쿠키를 사용한다. 발췌만으로 Edge Proxy의 최종 변환 경로 전체를 확인하지는 못했다.

컴파일 설명은 서버 액션·React Server Components 등의 Rust SWC 변환, NAPI 바인딩, 별도 WASM 빌드를 다룬다. 네이티브 패키지 선택과 일부 런타임 로딩 세부는 확인하지 못했다. 과거 시작 설명에는 `pnpm create next-app@latest my-app --yes`, `pnpm dev`, Node.js 20.9 이상이 제시됐다. 수집 당시 위키의 내용이며 두 과거 버전 모두에 검증된 호환성 조건은 아니다. 기본 선택지와 번들러 동작은 정확한 릴리스에서 확인해야 한다.
<!-- communication -->
저장된 설명은 `https://telemetry.nextjs.org/api/v1/record`로 익명·프로젝트·세션 식별자, 메타데이터와 이벤트 필드를 POST한다고 한다. 제어 방법으로 `NEXT_TELEMETRY_DISABLED=1` 또는 `next telemetry disable`을 제시한다. 5초 제한에 관한 과거 주장은 15.1.0 재질문에서 재현되지 않았다. 텔레메트리를 끄는 것으로 모든 네트워크 통신이 차단된다고 할 수는 없다. [출처: 과거 DeepWiki 외부 통신 설명]

`experimental.agentUpgrade`, `assessUpgrade`도 언급됐지만 목적지와 전송 데이터는 확인하지 못했다. 이후 위키에는 사용자 검토 후 선택적으로 제출하는 피드백 기능이 설명돼 있다. 이 동작들이 검토한 정확한 릴리스에 존재하는지 증명되지 않았다. OpenTelemetry는 `instrumentation.ts`와 앱이 선택한 수집기를 사용하는 것으로 설명되며, 프레임워크 텔레메트리 목적지와 구분해야 한다. `NEXT_OTEL_FETCH_DISABLED` 주장은 한 재질문에서 재현되지 않았으므로 제어 수단으로 쓰기 전에 검증한다.

설정 설명에는 `next.config.js`, `next.config.ts`, `.env` 계열이 있다. `NEXT_PUBLIC_` 값은 빌드 때 브라우저 번들에 포함되는 것으로 설명되므로 비밀에 이 접두사를 붙이면 안 된다. `SESSION_SECRET`, `server-only`, `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY`도 언급된다. 생성한 암호화 키를 `.rscinfo`에 저장한다는 주장은 재현되지 않아 여기서는 사실로 단정하지 않는다. 실제 비밀 값이나 비공개 환경 파일은 이 보고서에 포함하지 않는다.
<!-- roles -->
역할 설명은 `@next/env`를 환경 로딩, 플랫폼별 `@next/swc-*`를 네이티브 변환, `@swc/helpers`를 변환 코드 보조 함수, caniuse-lite를 브라우저 지원 데이터, postcss를 CSS 처리, sharp를 이미지 최적화, styled-jsx를 범위 지정 스타일로 제시한다. 15.1.0 설명에는 multipart 요청 파싱용 busboy도 있고 `@swc/counter` 역할은 미확인이다. 이는 AI 생성 설명이며 그래프의 패키지·버전 사실과 구분한다.

해석된 그래프에는 플랫폼별 이미지·컴파일러 패키지가 있다. 모든 패키지가 하나의 운영체제에 설치되거나 특정 앱 번들로 배포된다는 증거는 아니다. 실제 lockfile, 빌드와 배포 산출물을 추적한 뒤 적용되는 라이선스 의무를 판단해야 한다. 선택적 구성과 설치 조건에 따라 실제 의존성은 달라질 수 있다.
<!-- maintenance -->
저장된 Scorecard 총점은 6.2, 기준일은 2026-08-24다. 정책 v3는 Maintained 체크가 10이어도 유지보수를 조건부로 판정한다. 활발한 활동만으로 다른 측정 항목을 상쇄하지 않는다. Code-Review 9, Security-Policy 10이며, 의존성 고정·토큰 권한·바이너리 산출물·정적 분석에는 낮은 점수도 있다. Branch-Protection과 Signed-Releases는 미평가(-1)이고 Vulnerabilities 체크는 없다. [출처: `data.json#/get_project/scorecard`]

과거 설명은 Vercel의 프로젝트, 유지관리자 리뷰, stable·canary 릴리스 채널, Vercel HackerOne을 통한 비공개 보안 신고를 제시한다. 고정된 stable 릴리스 주기나 현재 신고 절차를 독립적으로 검증한 것은 아니다. 실제 신고에는 upstream의 최신 보안 정책을 따른다.
<!-- actions -->
1. 15.1.0의 알려진 높은 심각도 취약점은 해당 버전의 도입 차단 항목으로 본다. 대체 버전을 고르기 전에 권고별 생태계·영향 패키지·버전 분기를 대조한다. 수정 버전이 존재해도 15.1.0 자체가 안전해지지는 않는다.
2. 프레임워크를 올린 뒤 실제 해석된 postcss·sharp 버전을 확인한다. 검토와 관련 앱 테스트를 다시 실행한다. 프레임워크 버전이나 평탄화된 수정 버전 목록만으로 해결됐다고 추정하지 않는다.
3. 실제 배포되는 sharp/libvips 산출물의 LGPL 의무와 caniuse-lite CC-BY-4.0의 출처 표시 조건을 검토한다. 정책/3은 CC-BY-4.0을 unknown 대신 출처 표시 검토가 필요한 조건부로 분류한다. 해당 자료의 출처·라이선스 링크·변경 고지를 확인해야 한다.
4. 15.1.0의 busboy·streamsearch는 저장된 메타데이터 배열이 비어 있으므로 정확한 버전의 라이선스 파일을 확인한다. 빈 메타데이터가 라이선스 부재의 증거는 아니다.
5. 정확한 릴리스·배포 환경에서 텔레메트리 설정, 브라우저 노출 환경 변수, 이미지 처리 기능을 점검한다. 재현되지 않은 위키 설명에 의존하지 않는다.
6. 미확인 유지보수 관행을 기록하고 운영 승인 전에 최신 자료를 확보한다. 번역하거나 버전을 비교할 때 이 스냅샷은 보존한다.
<!-- limitations -->
기존 에이전트 검토 결과는 WARN이다. `.rscinfo` 키 저장, 일부 텔레메트리·기본 설정 등 DeepWiki 주장이 재현되지 않았다. 다른 일부 절도 다시 확인하지 않았다. 저장소 위키가 새 주요 버전을 설명할 수 있으므로 이것만으로 특정 버전의 실행 동작을 확정할 수 없다.

15.1.0의 기존 `data.json`에는 `deepwiki: null`이 들어 있다. 설명은 과거 마크다운에 남았지만 대응하는 원본 위키 블록을 저장하지 못해 확인할 수 없다. 설명 문단은 과거에서 이어받은 미검증 참고 자료로 취급한다. 16.4.6에는 저장된 위키 블록이 있지만 버전 적용 여부는 여전히 미확인이다. 두 버전 모두 공개 레지스트리 그래프를 실제 설치 앱과 대조하지 않았고, 기존 Scorecard는 수집 당시 85일 전 자료였다.
