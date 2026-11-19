# fastapi 0.163.1: 오픈소스 도입 검토서

자료 수집일: 2026-11-17T03:05:00Z · pypi · fastapi/fastapi · oss-gate.policy/2

> 과거 자료로 만든 예제입니다. 원본 스냅샷을 보존하고 정책 v2로 판정을 다시 계산했습니다. 실시간 검사 결과가 아닙니다.

**판정: 조건부**

FastAPI는 Python 타입 선언을 입력 검증, 직렬화와 API 문서화에 연결한다. 패키지의 MIT 메타데이터와 비어 있는 권고 목록은 긍정적인 관찰이다. 그러나 저장된 의존성 그래프는 요청한 0.163.1이 아니라 0.162.4의 자료다. 정책 v2는 이 미확인 범위 때문에 최종 판정을 조건부로 제한한다. 과거 보고서는 대체 버전의 그래프를 사용하고도 가능으로 판정했으며, 이 개정 예제는 원본 근거를 바꾸지 않고 그 동작을 바로잡는다.

## 1. 판정과 범위

| 영역 | 판정 |
|---|---|
| 라이선스 | 가능 |
| 알려진 취약점 | 가능 |
| 의존성 | 확인 필요 |
| 유지보수 | 확인 필요 |

도입 검토를 돕는 자료이며 법적 판단이나 보안 인증이 아닙니다. 공개 메타데이터는 불완전할 수 있습니다. DeepWiki 설명은 AI 생성 자료이며 검토 버전과 다를 수 있습니다.

과거 판정: `가능`. 현재 표는 동일한 저장 자료에 정책 v2를 적용한 결과다.

## 2. 이 소프트웨어는 무엇인가

저장된 DeepWiki는 FastAPI를 Starlette와 Pydantic 기반 프레임워크로 설명한다. 타입 선언으로 입력을 검증하고 데이터를 변환하며, OpenAPI·JSON Schema 문서를 Swagger UI와 ReDoc으로 제공한다. 의존성 주입으로 인증이나 데이터베이스 연결 같은 공통 구성요소를 조합한다. 위키는 HTTP Basic, OAuth2/JWT, API 키 기능도 설명한다. 이는 AI 생성 설명이며 해당 버전의 보안 테스트 결과는 아니다. [출처: `data.json#/deepwiki`]

애플리케이션은 `FastAPI`를 만들고 `APIRouter`를 포함한다. Starlette가 요청을 라우팅하고 핸들러가 폼 또는 바이트·JSON을 읽는다. `solve_dependencies()`가 경로·쿼리·헤더·쿠키·본문 값을 모아 검증한다. `run_endpoint_function()`은 비동기 핸들러를 기다리거나 동기 핸들러를 스레드풀에서 실행한다. 과거 위키 발췌에는 응답 생성·직렬화가 일부만 포함돼 있어 마지막 전체 처리 경로는 미확인이다. [출처: 저장된 DeepWiki 요청 흐름 답변]

과거 시작 예제는 `uv add "fastapi[standard]"`, `uv run fastapi dev`이며 localhost:8000과 `/docs`를 안내한다. 운영 명령은 `fastapi run`으로 설명됐다. 이 검토에서 실행한 명령은 아니며 standard extra가 저장된 그래프 밖의 패키지를 추가할 수 있다. 위키의 성능 주장은 프로젝트 자체 추정에 근거하므로 독립적인 벤치마크로 볼 수 없다.

## 3. 외부 통신과 설정

확인한 위키 자료에서는 FastAPI 자체의 별도 업데이트 검사나 일반 외부 API 호출을 찾지 못했다. 그러한 동작이 없다는 뜻은 아니다. 구체적으로 설명된 통신은 `FASTAPI_OTEL_AUTO_CONFIGURE=true` 또는 `telemetry={"auto_configure": True}`와 OTLP 목적지를 지정하는 OpenTelemetry 자동 설정이다. 설명된 경로는 `/v1/traces`, `/v1/metrics`, `/v1/logs`다. [출처: 저장된 DeepWiki 관측성 답변]

설명에 따르면 trace·metric·log에는 요청 정보와 처리되지 않은 예외의 유형·메시지·스택 트레이스가 포함될 수 있다. 검증 실패 로그에는 잘못된 입력값 대신 경로와 오류 수가 담긴다고 한다. 이 주장은 버전에 고정돼 있지 않으므로 운영 텔레메트리를 설정하기 전에 실제 설치 버전에서 확인해야 한다.

저장된 설정에는 `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`, 신호별 `tracing`·`metrics`·`logs`, 요청 `exclude`가 있다. 자동 설정을 꺼도 앱이 별도로 구성한 provider·exporter가 모두 꺼지는 것은 아니다. 실제 exporter 인증 헤더를 검토서에 넣지 않는다.

설정 예제는 `pydantic-settings`, `BaseSettings`, 선택적으로 `SettingsConfigDict`를 통한 `.env` 로딩을 사용한다. 캐시한 설정 의존성으로 재사용과 테스트 재정의를 지원한다. JWT 튜토리얼의 하드코딩된 `SECRET_KEY`는 운영 비밀 관리 방식이 아니다. 과거 설명에는 Argon2 비밀번호 해시와 존재하지 않는 사용자의 더미 해시 검증이 있으나, 토큰 저장·폐기와 실제 배포된 비밀 관리 시스템은 확인하지 않았다. [출처: 저장된 DeepWiki 설정 답변]

## 4. 라이선스 검토

`fastapi@0.163.1`: MIT.

분류는 법적 판단이 아니다. `unknown`은 자동 승인하지 않는 항목이며, 메타데이터 누락·미지원 식별자·미해석 예외를 포함한다. 여러 라이선스의 관계가 명시되지 않은 목록은 보수적으로 AND처럼 검토한다. OR 선택지는 선택·적용 근거를 기록해야 한다.

| 패키지 | 버전 | 라이선스 | Category | 의존성 경로 |
|---|---|---|---|---|
| annotated-doc | 0.0.6 | MIT | permissive | fastapi@0.162.4 → annotated-doc@0.0.6 |
| annotated-types | 0.8.0 | MIT | permissive | fastapi@0.162.4 → pydantic@2.14.3 → annotated-types@0.8.0 |
| anyio | 4.16.0 | MIT | permissive | fastapi@0.162.4 → anyio@4.16.0 |
| idna | 3.20.0 | BSD-3-Clause | permissive | fastapi@0.162.4 → anyio@4.16.0 → idna@3.20.0 |
| opentelemetry-api | 1.45.2 | Apache-2.0 | permissive | fastapi@0.162.4 → opentelemetry-api@1.45.2 |
| pydantic | 2.14.3 | MIT | permissive | fastapi@0.162.4 → pydantic@2.14.3 |
| pydantic-core | 2.50.4 | MIT | permissive | fastapi@0.162.4 → pydantic@2.14.3 → pydantic-core@2.50.4 |
| starlette | 1.10.0 | BSD-3-Clause | permissive | fastapi@0.162.4 → starlette@1.10.0 |
| typing-extensions | 4.16.0 | PSF-2.0 | permissive | fastapi@0.162.4 → typing-extensions@4.16.0 |
| typing-inspection | 0.4.5 | MIT | permissive | fastapi@0.162.4 → typing-inspection@0.4.5 |

**의존성 그래프가 다른 버전의 자료입니다. 요청 버전의 의존성은 확인되지 않았습니다.**

## 5. 알려진 취약점

이 스냅샷에서 알려진 권고가 반환되지 않았습니다. 취약점이 없다는 보장은 아닙니다.

별칭이 연결된 권고는 한 묶음으로 집계한다. 제목은 출처 원문이다. 점수 미상은 0점으로 바꾸지 않는다. 수정 버전 목록은 패키지·버전 분기를 대조하기 전에는 업그레이드 권고가 아니다.

## 6. 의존성

직접 의존성: 7 · 간접 의존성: 3 · graph version: `0.162.4`

대체 그래프는 annotated-doc을 문서 메타데이터, Pydantic을 검증·직렬화·스키마 생성, Starlette를 ASGI 라우팅·미들웨어, opentelemetry-api를 계측 인터페이스로 설명한다. anyio, typing-extensions, typing-inspection도 포함된다. 뒤의 타입 보조 라이브러리들의 구체적인 사용처는 위키에서 확정하지 못했다. [출처: `data.json#/get_dependencies`, 저장된 DeepWiki 의존성 답변]

출처 간 차이도 있다. 위키는 anyio를 테스트 그룹 의존성으로 설명했지만 deps.dev는 0.162.4 그래프에서 직접 의존성으로 분류했다. 런타임 의존성이 다섯 개라는 설명은 재현되지 않았고, 당시 후속 답변에는 `opentelemetry-api>=1.44.0`을 포함한 여섯 개가 나왔다. 원인은 해소되지 않았다. 어느 쪽도 0.163.1의 전체 그래프를 확정하지 못한다.

| Parent | Child |
|---|---|
| fastapi@0.162.4 | annotated-doc@0.0.6 |
| fastapi@0.162.4 | anyio@4.16.0 |
| fastapi@0.162.4 | opentelemetry-api@1.45.2 |
| fastapi@0.162.4 | pydantic@2.14.3 |
| fastapi@0.162.4 | starlette@1.10.0 |
| fastapi@0.162.4 | typing-extensions@4.16.0 |
| fastapi@0.162.4 | typing-inspection@0.4.5 |
| anyio@4.16.0 | idna@3.20.0 |
| anyio@4.16.0 | typing-extensions@4.16.0 |
| opentelemetry-api@1.45.2 | typing-extensions@4.16.0 |
| pydantic@2.14.3 | annotated-types@0.8.0 |
| pydantic@2.14.3 | pydantic-core@2.50.4 |
| pydantic@2.14.3 | typing-extensions@4.16.0 |
| pydantic@2.14.3 | typing-inspection@0.4.5 |
| pydantic-core@2.50.4 | typing-extensions@4.16.0 |
| starlette@1.10.0 | anyio@4.16.0 |
| typing-inspection@0.4.5 | typing-extensions@4.16.0 |

## 7. 유지보수

저장된 프로젝트 응답에는 Scorecard가 없고 다른 저장소의 자료를 대신 사용하지 않았다. 유지보수는 미확인 상태이며 stars·forks·issues는 참고 정보다. 릴리스 기록에는 11월 10일의 0.162.4부터 11월 15일의 0.163.1까지 중간 게시가 있다. 이는 기록된 릴리스 활동이며 향후 지원 약속은 아니다. [출처: `data.json#/get_project`, `data.json#/lookup_package/recent_versions`]

위키는 창립자와 기여자 커뮤니티, GitHub 이슈 템플릿을 통한 보안 연락 안내, Dependabot의 월간 uv 의존성 확인을 설명했다. 고정 릴리스 주기와 전체 유지보수 조직은 확정하지 못했다. 기존 보고서도 이 서술을 모두 독립적으로 확인하지는 않았다. [출처: 저장된 DeepWiki 유지보수 답변]

## 8. 도입 조치

1. 도입 결정 전에 FastAPI 0.163.1의 그래프를 확보하고 실제 설치 lockfile과 대조한다. 0.162.4 그래프는 참고 자료이므로 그 의존성 버전을 새 릴리스 환경에 강제로 적용하지 않는다.
2. 사용할 환경의 lockfile에 검토 대상과 해석된 의존성 버전을 기록한다. 업그레이드와 선택적 extras는 다시 검토한다.
3. 정확한 릴리스가 설명된 텔레메트리 설정을 지원하는지 확인한 뒤 허용할 신호와 목적지를 정한다. 예외·로그 내용과 별도로 설정된 exporter도 확인한다.
4. 운영 비밀은 배포 환경의 비밀 관리 절차로 주입한다. 튜토리얼 키를 복사하거나 `.env` 파일을 커밋하지 않는다.
5. 실제 해석된 패키지에서 고지 목록을 만들고 MIT·BSD·Apache·PSF 관련 고지를 검토한다.

## 9. 확인하지 못한 것

미확인 범위: graph_root_unverified, graph_version_unverified

최초 수집 때 요청한 버전의 그래프가 없었다. 0.163.0, 0.162.7, 0.162.6, 0.162.5를 거쳐 0.162.4를 얻었으며 총 다섯 번 대체 조회했다. 의존성 열 개에 관한 라이선스·취약점 관찰은 모두 이 이전 그래프에 해당한다. 거기에 알려진 취약점이 없다는 결과로 0.163.1까지 확인했다고 할 수 없다.

기존 에이전트 검토 결과는 WARN이며 Scorecard 부재, 해소되지 않은 의존성 설명, 재질문하지 않은 위키 절이 남아 있다. 패키지 API의 버전 수는 368, 프로젝트 매핑의 버전 수는 390으로 차이를 설명하지 못했다. Go 의사 패키지와 fastapi-slim 대신 pypi/fastapi를 선택했다. 위키 답변은 전체 페이지 열람이 아닌 요약이며 요청 릴리스에 고정되지 않았다. 이 한계는 두 언어에 동일하게 남긴다.

## 10. 근거와 검증

| 주장 | 출처 |
|---|---|
| 라이선스 | data.json#/lookup_package/licenses |
| 의존성 | data.json#/get_dependencies |
| 알려진 취약점 | data.json#/advisories |
| 유지보수 | data.json#/get_project/scorecard |
| DeepWiki | data.json#/deepwiki |

검증 상태: **WARN**. 원본 JSON 해시와 정책 재계산·언어별 수치 표를 확인했다. 과거 외부 응답의 진위와 위키 서술 전체를 새로 확인한 것은 아니다.

SHA-256 (`data.json`): `9c119652268042677ecbfe97e2f20620e98be40d8dc42276480403ac61dc7a47`

[deps.dev](https://deps.dev/) · [OSV](https://osv.dev/) · [DeepWiki](https://deepwiki.com/fastapi/fastapi)

출처·이용 조건은 [NOTICE](../../NOTICE.md)를 참고한다.
