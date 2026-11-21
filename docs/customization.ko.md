# 선택적 정책과 CLI

[English](customization.md)

일반 OSS Gate 사용에는 설정이 필요하지 않습니다. 기존처럼 플러그인에 자연어로 요청하면 됩니다. 정책을 명시적으로 선택한 검토에만 추가 규칙을 적용하고, 보고서에도 그때만 기본 판정과 추가 정책 적용 결과를 구분해 표시합니다.

## 정책 선택

MCP를 사용할 때는 두 로컬 서버 `depsdev`와 `deepwiki` 각각의 환경에 `OSS_GATE_POLICY`를 절대 경로로 지정한 뒤 다시 시작합니다. CLI는 `cli.py --policy /절대경로/settings.json <명령>` 또는 같은 환경 변수를 사용합니다. 환경 변수로 선택한 정책을 다른 CLI 경로로 교체할 수 없습니다.

수동으로 등록한 서버의 기존 설정에 다음 환경 변수 항목을 추가할 수 있습니다. 전체 클라이언트 설정이 아닌 서버 설정의 일부입니다.

```json
{"env": {"OSS_GATE_POLICY": "/absolute/settings.json"}}
```

한쪽 서버의 설정이 다른 쪽에도 전달된다고 가정하지 마세요. 검토 대상 저장소 안의 설정 파일을 자동으로 읽지 않습니다. 통제가 필요한 환경에서는 정책 파일을 신뢰하지 않는 프로젝트 밖에 두고, 호스트 권한으로 변경을 제한해야 합니다.

[정책 예시](../plugins/oss-gate/policies/example.json)는 자동 적용되지 않습니다. 이 예시는 DeepWiki를 끄고, 예시 사내 이름을 차단하고, 7일의 신규 버전 대기 기간과 외부 통신 근거를 요구합니다. 제품 기본값이나 모든 회사에 권장하는 기준은 아닙니다.

## 설정 범위

| 항목 | 의미 |
|---|---|
| `network.allowed_repository_hosts` | 저장소 식별자의 정확한 호스트 허용 목록. 생략하면 기존 동작, 빈 목록이면 저장소 조회 차단 |
| `network.npm_registry_url` | deps.dev 404 후 존재 확인에 사용할 HTTPS npm 미러 기본 주소 |
| `network.services` | 허용할 서비스. 생략하면 기존 서비스 사용, 빈 목록이면 모두 차단 |
| `network.deny_identifiers` | `npm:@internal/*`, `repo:company/*` 같은 식별자 패턴 차단 |
| `network.allow_identifiers` | 명시한 식별자만 허용. 생략하면 허용 목록 검사 없음, 빈 목록이면 패키지·저장소 조회 차단 |
| `review.minimum_release_age_days` | 0~3650일. 기본 0으로 비활성. 기간 미충족은 조건부 |
| `review.require_communication_review` | 기본 false. 필요한 검토 자료가 없거나 불완전하면 조건부 |
| `review.blocked_destinations` | 금지 목적지의 호스트 또는 `*.example.org` 형태 |

식별자는 `npm:`, `pypi:`, `go:`, `maven:`, `cargo:`, `nuget:`, `rubygems:`, `repo:` 접두사를 사용합니다. GitHub 저장소 값은 `owner/repo`이고, 다른 호스트는 `host/owner/repo` 형태로 호스트와 하위 그룹을 유지합니다. `repo:company/*`는 GitHub 조직, `repo:*.example.internal/*`는 사내 도메인의 하위 호스트에 대응합니다. 차단 목록이 우선하며 `*`는 `/`도 포함할 수 있습니다. PyPI 이름의 구두점·대소문자와 npm·NuGet·저장소 이름의 대소문자는 비교 전에 정규화합니다. 허용 목록은 취약점 권고 ID에는 적용되지 않습니다.

공개 여부를 확인하려고 외부 조회하면 이미 이름을 전송한 셈입니다. 엄격한 환경에서는 로컬 허용 목록을 직접 정해야 합니다. 서버가 반환한 의존성도 전송 전에 검사합니다. OSV 요청 묶음에 차단된 이름이 있으면 묶음 전체를 보내지 않고 미확인으로 남깁니다.

## 판정 근거와 한계

발행 시각이 없거나 잘못됐거나 평가 시각보다 미래이면 확인 필요로 남깁니다. 오래된 릴리즈라는 이유로 유지보수 중단이라고 판단하지 않습니다. 긴급 보안 패치는 별도 사람의 판단이 필요할 수 있고, 대기 규칙 때문에 취약한 버전을 유지하라고 권고하지 않습니다.

외부 통신 규칙은 사용자가 명시적으로 제공한 [검토 자료](../plugins/oss-gate/policies/communication.example.json)를 평가합니다. MCP의 `communication_path` 또는 CLI의 `collect --communication`에 절대 경로를 지정합니다. 확인 완료 자료에는 정확한 패키지·버전, 출처, 검토자, 시간대가 있는 검토 시각이 필요합니다. AI 설명만으로 확인 완료로 바꾸거나 검토자를 만들어내면 안 됩니다. 현재 통신 항목은 HTTP(S) 목적지를 표현합니다. 다른 프로토콜이나 미확인 목적지가 관련되면 조회 범위를 불완전한 상태로 남겨야 합니다. 프로그램이 검증하는 것은 자료의 형식과 적용 대상이며, 검토자의 진술 자체를 독립적으로 검증하지는 않습니다.

확인된 자료에서 금지 목적지로 필수 또는 기본 활성화된 통신이 있으면 보류, 활성화 조건이 불명확하면 조건부입니다. 선택 기능이며 기본 비활성화임이 명시된 목적지는 그 자체로 막지 않습니다. 이는 공개된 기본 동작에 대한 검토이며 실제 설치 환경을 검사한 결과가 아닙니다. 자료가 없으면 조건부 결과를 유지하세요.

기본 판정은 추가 정책으로 완화하지 않습니다. 정책 내용·해시·평가 시각을 근거와 함께 보존하고, HTML을 다시 만들 때 현재 시각이나 현재 정책으로 바꾸지 않습니다. 서로 다른 추가 정책의 결과는 포트폴리오에서 섞어 비교하지 않습니다. 기존 보고서는 자동 변경되지 않습니다.

## CLI 사용

저장소 루트에서 다음과 같이 실행할 수 있습니다.

```sh
uv run --frozen --project plugins/oss-gate python plugins/oss-gate/cli.py plan pypi requests --version 2.34.2 --repo psf/requests
uv run --frozen --project plugins/oss-gate python plugins/oss-gate/cli.py collect pypi requests --version 2.34.2 --output-root /absolute/reviews
uv run --frozen --project plugins/oss-gate python plugins/oss-gate/cli.py explain psf/requests --topic overview --out /absolute/review/deepwiki.json
uv run --frozen --project plugins/oss-gate python plugins/oss-gate/cli.py render /absolute/review --language both
```

`plan`은 최초 전송 대상의 로컬 미리보기입니다. 조회 후 알게 되는 의존성·권고까지 미리 열거하지 않으며, 후속 요청마다 정책을 검사합니다. `collect`는 원문 근거를 저장하고 요약과 경로를 출력합니다. 사용자의 에이전트가 `review.ko.md` 또는 `review.en.md`를 작성한 뒤 `render`로 HTML을 만듭니다. CLI 자체가 별도 모델 API를 호출해 글을 쓰지는 않습니다.

`explain`은 정해진 주제 `overview`, `communication`, `dependencies`, `maintenance` 중 하나로 외부 DeepWiki를 조회하고 새 JSON 파일에 응답 전체를 저장합니다. 상위 폴더는 존재해야 하며, 주제별로 다른 파일명을 사용하세요. 실행 오류는 종료 코드 1이고, 정상적으로 수집된 보류 판정은 실행 오류가 아닙니다. CLI만 사용할 때는 MCP를 함께 등록할 필요가 없습니다.

CLI도 외부 서비스를 사용합니다. 최초 uv 실행에는 의존성 다운로드가 필요할 수 있습니다. 토큰 절감 폭은 도구 지연 로딩과 출력 사용 방식에 따라 다르며, 실측된 절감률을 주장하지 않습니다.

## 통제 범위

OSS Gate를 통한 요청에만 적용됩니다. 다른 MCP, 셸, 브라우저, 모델 제공자로의 전송과 uv 초기 설치는 통제하지 않습니다. 코드·환경 변수·정책 파일을 변경할 수 있는 사용자는 우회할 수 있으므로 회사의 호스트·네트워크 통제도 필요합니다. 기존에 직접 연결한 원격 DeepWiki는 로컬 연결 모듈로 교체해야 합니다.

보고서와 정책에는 조직 이름·검토자 정보가 포함될 수 있습니다. 공유 전에 확인하세요. 중앙 로그 서버, 자체 텔레메트리, 별도 모델 키는 추가하지 않습니다. 개발 세부 사항은 [실행 참조](../plugins/oss-gate/skills/oss-review/references/execution.md)에 있습니다.

## 저장소 호스트와 npm 미러

`allowed_repository_hosts`에는 `["github.com"]`처럼 정확한 호스트를 지정합니다. 대소문자, 마지막 점, IDNA 표기를 정규화합니다. 와일드카드·포트·URL 경로는 허용하지 않습니다. 이는 API 서버 주소와 별개로, 외부 서비스에 전달할 **저장소 식별자의 호스트**를 제한합니다. API에서 발견한 저장소에도 적용하며 기존 식별자 차단 규칙이 계속 우선합니다. 호스트를 허용해도 DeepWiki가 사내 GitHub를 지원하게 되는 것은 아닙니다.

`npm_registry_url`은 `https://registry.example.internal/repository/npm/`처럼 HTTPS 주소에 기본 경로와 포트를 붙일 수 있습니다. [미러 예시](../plugins/oss-gate/policies/npm-mirror.example.json)는 자동 적용되지 않습니다. 기존 `npm` 서비스와 패키지 식별자 규칙이 적용되며 `plan`에서 선택된 주소를 로컬로 확인할 수 있습니다.

미러는 deps.dev가 404를 반환했을 때만 패키지·버전 존재 확인에 사용합니다. 미러 장애 시 공개 npm으로 넘어가거나 리디렉션을 따르지 않습니다. 미러의 404는 `mirror_package_not_found` 또는 `mirror_version_not_found`로 구분하며, 동기화 지연·접근 정책의 영향일 수 있어 공개 npm에도 없다는 뜻이 아닙니다. 미러에서 발견되어도 deps.dev 분석 근거를 대신하거나 공개 패키지와 내용이 같음을 보증하지 않습니다.

이번 구현은 npm 호환 JSON 응답을 제공하고 OSS Gate의 별도 인증정보 없이 조회 가능한 미러를 대상으로 합니다. 인증 오류는 미확인으로 남깁니다. URL에 인증정보를 넣을 수 없으며 `.npmrc`·인증정보를 자동으로 읽거나 TLS 검증을 끄지 않습니다. PyPI 미러와 완전한 폐쇄망 분석은 지원 범위에 포함되지 않습니다.

MCP를 등록하지 않으려면 [설치 안내](installation.ko.md)의 `oss-gate-cli`를 선택하세요. 저장소 조회는 `project <repo> --out <새 JSON>`, 매니페스트 검사는 `audit <로컬에서 정리한 파일> --type requirements.txt --out <새 JSON>`으로 실행합니다. 나머지 명령과 동일하게 `uv run --frozen --project <플러그인 경로> python <플러그인 경로>/cli.py` 뒤에 붙입니다. 출력 폴더는 미리 존재해야 하며 원문 응답은 새 JSON 파일에 보존합니다.

## 추가 CA 인증서

사내망에서 HTTPS 인증서를 회사 CA로 다시 서명한다면, 기존 certifi 신뢰 목록에 회사의 공개 CA 인증서를 명시적으로 추가할 수 있습니다.

```json
{
  "schema": "oss-gate.settings/1",
  "name": "Company CA",
  "version": "1",
  "network": {"additional_ca_file": "/absolute/path/company-ca.pem"}
}
```

OSS Gate가 실행되는 컴퓨터의 절대 경로를 사용합니다. Windows JSON 예시는 `"C:\\Company\\company-ca.pem"`입니다. 파일은 공개 인증서만 담은 PEM 형식이며 최대 1 MiB입니다. 개인 키를 넣지 마세요. 조직의 신뢰할 수 있는 관리자에게 받은 인증서를 사용합니다. 설정을 생략하면 기존 동작을 유지합니다. OS 신뢰 저장소를 선택하는 기능은 이번 범위에 포함하지 않았으며, 필요한 공개 CA를 PEM 파일로 내보내서 지정합니다.

deps.dev·OSV·레지스트리·미러·DeepWiki 요청에 같은 추가 CA를 적용합니다. 인증서 체인·호스트명·만료 검증은 유지하며, 기존 서비스·식별자 제한과 리디렉션 차단도 계속 적용됩니다. `trust_env=False`를 유지하므로 프록시·CA 경로 환경 변수를 자동 적용하지 않습니다. 프록시 주소나 클라이언트 인증을 설정하는 기능은 아니며, 다른 에이전트 도구와 uv 최초 의존성 설치에는 적용되지 않습니다.

작업마다 파일을 한 번 읽고 전용 연결 풀을 사용합니다. 의존성 조회 스레드는 해당 작업의 연결만 공유합니다. 파일을 읽을 수 없거나 형식·크기가 잘못되면 HTTP 요청 전에 `tls_configuration_invalid`로 종료하고 다른 신뢰 설정으로 넘어가지 않습니다. `plan`은 설정 형식만 확인하므로 인증서가 실제로 준비됐다는 뜻은 아닙니다. `collect`는 실제 CA 파일의 SHA-256과 certifi 버전을 `data.json`의 `tls_trust`에 보존하며, 이후 오프라인 판정·HTML 생성에는 원래 파일이 필요하지 않습니다. 같은 경로라도 파일을 바꾸면 다음 작업에는 변경된 인증서를 적용합니다.

추가한 CA가 발급한 인증서는 기존 정책이 허용한 목적지에 대해 신뢰하게 됩니다. HTTPS 검사 프록시는 요청 내용을 읽을 수 있으므로 사내 이름 전송 제한도 계속 필요합니다. 저장된 정책에는 로컬 CA 파일 경로가 포함되니 보고서 공유 전에 확인하세요. 인증서 내용이나 개인 키는 보고서에 저장하지 않습니다.
