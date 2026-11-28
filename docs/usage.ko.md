# 사용 안내

[English](usage.md)

## 레포 전체 의존성 심사

로컬 레포·모노레포의 Yarn Berry(`package.json`, `yarn.lock`), Go(`go.mod`, `go.work`), Cargo(`Cargo.toml`, `Cargo.lock`), Java/Kotlin 해결 결과, Swift pin과 컨테이너 검사 보고서를 함께 분석합니다. 생태계·이름·버전 단위로 중복 없이 조회하고, 사용 프로젝트·취약점·라이선스·미확인 항목을 한 보고서에 표시합니다. 레포 URL을 공개 패키지 하나에 연결하는 기존 기능과 별도입니다.

```sh
uv run --frozen --project plugins/oss-gate python plugins/oss-gate/cli.py repo-plan /absolute/repository --output-root /absolute/reviews
uv run --frozen --project plugins/oss-gate python plugins/oss-gate/cli.py repo-collect /absolute/repository --public-packages --output-root /absolute/reviews --language both
uv run --frozen --project plugins/oss-gate python plugins/oss-gate/cli.py repo-render /absolute/reviews/saved-run --language both
```

`repo-plan`은 네트워크 없이 파일·패키지 목록을 보여줍니다. 패키지 식별자가 공개 정보임을 확인한 경우에만 `--public-packages`를 사용합니다. 사설 패키지가 섞여 있다면 명시적으로 선택한 정책의 `network.allow_identifiers`로 전송 대상을 제한하고 이 플래그를 생략할 수 있습니다. 기존 통신 정책과 추가 CA 설정은 그대로 적용됩니다. 설치·빌드 스크립트 실행이나 소스코드 업로드는 하지 않습니다.

수집은 새로운 폴더에 근거 JSON·API 원문·해시를 저장하고 선택 언어의 Markdown·HTML을 생성합니다. `repo-render`는 같은 근거를 검증해 보고서를 다시 생성합니다. 이 명령은 생성된 보고서를 덮어쓰므로 별도 편집 원고는 다른 파일에 보관하세요. MCP에서는 `plan_repository`, `collect_repository`를 사용하고, 반환된 폴더를 CLI `repo-render`로 렌더링합니다.

현재 판정 범위는 **Yarn Berry·Cargo·Gradle·Swift 잠금 버전, Maven 해결 버전과 Go 선언 버전의 취약점·확보한 라이선스**이며 컨테이너 가져오기는 별도로 평가합니다. 개발·선택·플랫폼별 의존성을 포함하며 실제 설치·배포 목록을 확정하지 않습니다. patch·Git·로컬 출처, peer 연결, 선언과 lockfile 불일치는 미확인입니다. Java/Kotlin·Swift·컨테이너의 심사 범위는 아래와 같습니다. Python 등 미지원 파일은 미확인으로 남깁니다. 소스코드 결함과 유지보수도 현재 레포 판정 범위에 포함하지 않습니다.

Go는 명령을 실행하지 않고 모듈·workspace의 대체 규칙과 제외 버전을 해석합니다. `go.sum`·`go.work.sum`은 설치 목록이 아니므로 파일 해시만 보존합니다. Go 버전은 **선언 버전**으로 표시하고 실제 빌드 선택 버전·전체 그래프 미확인을 남깁니다. 로컬 대체나 충돌한 workspace 규칙이 있으면 원래 모듈 이름으로 조회하지 않습니다. [Go 모듈 공식 문서](https://go.dev/ref/mod)를 기준으로 구분합니다.

Cargo는 lock 형식 3/4, workspace·별칭·상속·레포 내부 path 의존성과 간접 연결을 분석합니다. crates.io 출처만 공개 crate로 조회하며 Git·대체 레지스트리·patch·미지원 버전 조건·미확인 로컬 항목은 미확인으로 남깁니다. 발견한 `.cargo/config[.toml]`은 미지원 설정으로 표시하고 외부 설정은 심사 범위에 포함하지 않습니다. lock 목록에는 배포하지 않는 플랫폼·기능의 항목도 포함될 수 있습니다. [Cargo workspace](https://doc.rust-lang.org/cargo/reference/workspaces.html)·[의존성 해석 공식 문서](https://doc.rust-lang.org/cargo/reference/resolver.html#lock-file)를 참고하세요.

기본 조회 한도는 고유 패키지·버전 2,000개이며 `--max-packages`로 1~10,000개를 지정할 수 있습니다. 상세 취약점 한도는 1,000개입니다. 한도 도달·조회 실패·미지원 파일은 전체 판정의 미확인 사유로 남습니다. 검사율의 분모는 식별된 생태계·패키지·버전 수이며 해석하지 못한 파일까지 포함한 전체 검사율이 아닙니다. 기존 패키지 보고서용 집계·재판정 명령은 새 레포 스냅샷을 아직 지원하지 않습니다.

### Java/Kotlin·Swift·Docker

| 생태계 | 필요한 입력 | 주요 한계 |
| --- | --- | --- |
| Maven의 Java/Kotlin | 각 모듈의 `pom.xml` 옆 `dependency-tree.json` | 해결된 좌표·scope·연결을 사용하고 verbose 트리의 선택 제외 항목은 조회하지 않습니다. POM 버전 조건만으로는 부족합니다. |
| Gradle의 Java/Kotlin | `build.gradle[.kts]`와 `gradle.lockfile`, `buildscript-gradle.lockfile` 또는 구형 `gradle/dependency-locks/*.lockfile` | configuration을 보존합니다. 직접·간접 연결과 빌드 설정은 미확인입니다. |
| Swift | Xcode 하위 경로를 포함한 `Package.resolved` v1/v2/v3 | 버전이 있는 HTTPS Git pin을 OSV SwiftURL로 조회합니다. branch·revision 전용, registry·로컬 pin은 미확인입니다. 라이선스 공급원이 없어 보류가 유지됩니다. |
| Docker | Dockerfile·Compose 선언과 네이티브 `trivy.json` / `*.trivy.json` / `grype.json` / `*.grype.json` | 오프라인 가져오기입니다. 저장소와 digest가 정확히 일치할 때만 선언과 연결합니다. 이미지를 pull·빌드하거나 스캐너를 실행하지 않습니다. |

해결 결과는 프로젝트의 정상 개발·CI 절차로 준비하세요. Maven Dependency Plugin 3.7 이상에서는 `mvn dependency:tree -DoutputType=json -DoutputFile=dependency-tree.json`처럼 내보낼 수 있습니다. Gradle lock 생성과 Swift 의존성 해결은 프로젝트 코드를 실행할 수 있어 OSS Gate가 자동 실행하지 않습니다. SwiftURL은 `https://`와 `.git`을 뺀 `host/owner/repository`로 조회하고 식별자 정책에는 `swift:github.com/owner/*`를 사용할 수 있습니다. 비표준 짧은 이름으로 등록된 취약점 별칭은 미확인으로 남깁니다. JVM 동적·SNAPSHOT 버전, classifier, 저장소·프로필 설정, Swift mirror와 오래된 manifest는 미확인으로 남깁니다. 내보낸 파일은 제외 디렉터리인 `target`, `build`, `dist` 밖에 두세요.

별도로 허용한 이미지 검사에서는 `trivy image --scanners vuln --list-all-pkgs --format json --output trivy.json IMAGE@sha256:DIGEST` 또는 `grype IMAGE@sha256:DIGEST -o json > grype.json`처럼 준비할 수 있습니다. 실제 이미지와 digest를 넣으세요. 텍스트·SBOM이 아닌 네이티브 이미지 검사 JSON을 사용합니다. 유효한 컨테이너 보고서만 있는 레포는 `--public-packages` 없이 `repo-collect`할 수 있고, 일반 패키지가 섞여 있으면 공개 식별자 확인 또는 허용 목록이 필요합니다.

스캐너가 억제·무시한 취약점도 판정에 포함하고 가져온 패키지 라이선스에도 선택 정책을 적용합니다. 보고서·취약점 건수는 온라인 조회율과 별도로 표시합니다. 태그만으로는 이미지 내용이 확정되지 않으며 기반 이미지 보고서는 최종 빌드를 검사한 근거가 아닙니다. 0건이어도 전체 범위·취약점 DB 최신성·필터 부재를 보장하지 않습니다. 입력 SHA-256과 정규화한 결과를 봉인하며 이미지 환경변수와 스캐너 설정 원문은 제외합니다. 원본 검사 파일은 감사용으로 별도 보관하세요. Docker Hub/Scout는 이 어댑터에서 조회하지 않습니다.

형식 근거: [Maven JSON 트리](https://maven.apache.org/plugins/maven-dependency-plugin/examples/tree-mojo.html), [Gradle 잠금](https://docs.gradle.org/current/userguide/dependency_locking.html), [OSV 생태계](https://ossf.github.io/osv-schema/#affectedpackage-field), [Trivy 보고서](https://trivy.dev/latest/docs/configuration/reporting/), [Grype JSON 출력](https://github.com/anchore/grype), [Docker Scout](https://docs.docker.com/scout/).

## 패키지 검토

`oss-review`에 공개 저장소, 패키지·버전 또는 지원하는 manifest를 지정합니다. 언어는 `ko`, `en`, `both` 또는 자연어로 선택합니다. 명시한 선택이 우선이며, 없으면 요청 언어를 따릅니다. 버전이 없으면 수집 시점 레지스트리 기본 버전을 사용합니다. 저장소에 대응하는 패키지가 모호하면 확인하고, 임의로 고르지 않습니다.

패키지 검토는 `collect_review` MCP 또는 CLI `collect`로 고유한 근거 폴더를 만듭니다. 출력 루트에는 워크스페이스의 절대 경로를 지정합니다. `data.json`은 정리된 근거·판정, `api-responses.json`은 공개 API JSON 원문, `evidence-sha256.json`은 두 파일의 해시입니다. DeepWiki와 에이전트 검증 자료는 별도로 둡니다. 호스트 도구가 DeepWiki 원문 저장을 지원하지 않으면 전사한 자료임을 표시해야 합니다.

초기 패키지 조회가 실패하면 검토 폴더를 만들지 않고 원인과 다음 행동을 반환합니다. deps.dev의 404만으로 패키지가 없다고 단정하지 않습니다. npm·PyPI는 공개 레지스트리를 추가 확인해 자료 미제공, 패키지 부재, 버전 부재, 확인 불가를 구분합니다. npm 미러를 명시하면 이 추가 확인에 공개 npm 대신 미러를 사용하며, 미러의 부재 응답은 해당 미러에만 적용됩니다. 다른 생태계와 PyPI 미러는 확인하지 않습니다. 일시적인 오류는 한 번만 재시도하며, 서버가 2초를 넘는 대기를 요구하면 자동 재시도를 멈춥니다. 에이전트는 실패 원인을 선택한 언어로 설명하고, 이름·버전 확인이나 나중 재시도를 안내해야 합니다. 패키지의 존재가 확인되어도 분석 근거가 없으면 승인할 수 없습니다.

기존 두 언어 검토서를 체크아웃에서 렌더링하려면:

```sh
uv run --frozen --project plugins/oss-gate python plugins/oss-gate/render.py examples/reviews/psf-requests-2.34.2 --language both
```

선택한 언어의 마크다운이 먼저 있어야 합니다. 렌더러는 번역하거나 새 자료를 조회하지 않습니다. HTML은 외부 리소스 없이 열리고 출처 텍스트를 안전하게 표시하며 브라우저 인쇄를 지원합니다. 다운로드 링크를 쓰려면 마크다운·JSON도 같은 폴더에 유지합니다. 기존 `review.md`는 한국어 입력으로만 호환합니다.

기존 검토서의 번역을 요청하면 동일한 스냅샷을 유지합니다. 갱신을 요청하면 날짜가 다른 새 검토를 만듭니다. 갱신으로 판정이 바뀔 수 있지만 번역만으로 바뀌면 안 됩니다.

`audit_manifest`는 package.json, requirements.txt, go.mod의 직접 선언을 확인합니다. lockfile 해석이나 실제 설치 버전 탐지는 하지 않습니다. 범위·로컬 대체 경로는 제외하고, optional·peer·개발 그룹은 구분합니다. requirements의 환경 조건을 평가하지 않으며 간접 의존성도 발견하지 않습니다. 전체 프로젝트 검사가 아닌 범위를 한정한 manifest 점검입니다.

`periodic-report`는 선택한 기존 검토를 집계하고 누락 자료를 이유와 함께 제외합니다. `proposal-draft`는 기존 결과를 도입 제안으로 정리하되 가정·사람의 결정·미측정 결과를 드러냅니다. 둘 다 요청 없이 자료를 갱신하지 않으며 같은 언어 선택을 지원합니다.

과거 예제는 보존된 스냅샷을 두 언어로 다시 작성한 개정판입니다. 예전 문장을 모두 직역하지는 않았습니다. 잘못된 승인 규칙이나 근거 부족 주장은 교정·표시했고, 원본 근거 JSON은 개정된 예제와 함께 보관합니다.
