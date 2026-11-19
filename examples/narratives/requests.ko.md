<!-- summary -->
Requests는 외부 API를 호출하는 코드를 간결하게 작성할 수 있도록 돕는 Python HTTP 클라이언트다. 패키지 자신의 Apache-2.0 메타데이터는 이 프로젝트의 분류 정책을 통과한다. 이 스냅샷에서 도입 전 확인할 항목은 직접 의존성 certifi의 MPL-2.0 라이선스이며, 이에 따라 조건부로 판정한다. 실제 수정·배포 방식을 검토한 뒤 사람의 도입 결정을 별도로 기록해야 한다.
<!-- overview -->
Requests는 HTTP 메서드, 매개변수, JSON, 폼, 업로드, 스트리밍, 인증, 쿠키와 세션을 작은 API로 제공한다. 저장된 DeepWiki 설명에는 urllib3를 이용한 연결 풀과 keep-alive, TLS 검증, Basic/Digest 인증, 응답 디코딩이 포함돼 있다. 이 설명은 AI가 생성한 저장소 요약이며 검토 버전을 실행해 확인한 결과는 아니다. [출처: `data.json#/deepwiki`]

`Session.request`는 `Request`를 만들고 `PreparedRequest`로 준비하면서 쿠키, 헤더, 인증과 훅 같은 세션 설정을 합친다. `prepare_body`가 본문 형식을 처리하고, `merge_environment_settings`가 프록시와 TLS 설정을 반영한다. `Session.send`는 `HTTPAdapter`를 선택해 urllib3에 네트워크 작업을 위임한다. 반환된 `Response`에는 훅, 쿠키와 리다이렉트 처리가 이어진다. 사용자 정의 어댑터를 마운트할 수도 있다. [출처: 저장된 DeepWiki 요청 흐름 답변]

과거 사용 예제는 `requests.get(url, params=..., auth=...)`이며 JSON 본문에는 `json=...`, 지속되는 설정에는 `Session`을 사용한다. 위키는 Python 3.10 이상과 PyPy 지원을 설명한다. 위키가 버전에 고정돼 있지 않으므로 실제 도입할 릴리스의 런타임 호환성을 별도로 확인해야 한다.
<!-- communication -->
핵심 기능은 애플리케이션이 지정한 목적지에 요청을 보내는 것이다. 호출 방식에 따라 URL, 헤더, 자격 증명, 쿠키와 본문이 전송될 수 있다. 확인한 위키 설명에서는 별도 제품 텔레메트리를 찾지 못했지만, 이 제한된 관찰만으로 모든 코드 경로에 추가 통신이 없다고 단정할 수는 없다. [출처: 저장된 DeepWiki 외부 통신 답변]

저장된 설명은 `trust_env=True`를 기본값으로 제시한다. 프록시 환경 변수(`http_proxy`, `https_proxy`, `no_proxy`, `all_proxy`), `REQUESTS_CA_BUNDLE`, 대체값 `CURL_CA_BUNDLE`, `.netrc`가 요청에 영향을 줄 수 있다. 배포 환경을 점검하고 이러한 설정을 사용하지 않으려면 `Session.trust_env=False`를 검토한다. TLS 검증은 유지한다. 사설 CA가 필요하면 해당 릴리스의 `verify=<path>` 또는 CA 번들 설정을 확인한다. [출처: 저장된 DeepWiki 설정 답변]

클라이언트 인증서와 개인 키는 파일 권한과 비밀 저장 방식을 따로 검토해야 한다. 과거 위키는 클라이언트 키가 암호화되지 않은 형태여야 한다고 설명했으나 여기서 직접 실행해 검증하지는 않았다. 호스트 변경 리다이렉트에서 인증 헤더를 제거한다는 주장은 당시 재질문에서 재현되지 않았으므로 검증된 보안 보장으로 취급하면 안 된다. 예제에는 실제 자격 증명 값이 없다.
<!-- roles -->
저장된 그래프의 직접 의존성 네 가지는 역할이 다르다. certifi는 CA 인증서를, charset-normalizer는 문자 인코딩 탐지를, idna는 국제화 도메인 이름을, urllib3는 연결 풀과 HTTP 전송을 담당한다. 역할은 AI가 생성한 DeepWiki 설명에, 정확한 버전과 경로는 deps.dev 데이터에 근거한다. [출처: `data.json#/deepwiki`, `data.json#/get_dependencies`]

선택적 extras를 켜면 검토 범위가 달라진다. 과거 설명은 `socks`에 PySocks, `use_chardet_on_py3`에 chardet이 추가되며, chardet이 설치되면 charset-normalizer보다 먼저 선택될 수 있다고 한다. 이 추가 패키지는 직접 의존성 네 개의 스냅샷에 포함되지 않는다. `security` extra는 비어 있다고 설명됐다. extras를 켜거나 이 동작에 의존하기 전에 정확한 패키지 메타데이터를 확인해야 한다.
<!-- maintenance -->
저장된 Scorecard 기준일은 2026-08-24로, 최초 검토일보다 85일 전이다. 현재 저장소를 측정한 결과가 아니다. Maintained 10, Code-Review 8, Security-Policy 10이며, Pinned-Dependencies는 5, Signed-Releases와 CII-Best-Practices는 0이다. Branch-Protection은 평가하지 못해 -1이고, 응답에는 Vulnerabilities 체크가 없다. PyPI attestation 링크와 Signed-Releases 점수는 서로 다른 근거를 다루며 과거 검토에서 차이를 해소하지 못했다. [출처: `data.json#/get_project/scorecard`]

과거 설명은 psf 조직의 유지보수와 비공개 보안 권고 신고 절차를 제시한다. 응답·수정 목표도 언급하지만 이번에 독립적으로 확인하지 않았으며 서비스 보장으로 볼 수 없다. 보안 문서 링크에 관한 주장도 당시 재질문에서 재현되지 않았다. 실제 취약점을 신고할 때는 최신 upstream 보안 정책을 확인한다. [출처: 저장된 DeepWiki 유지보수 답변]
<!-- actions -->
1. 의도한 배포 방식에서 certifi의 MPL-2.0 의무에 관한 사람의 결정을 기록한다. certifi 파일 수정 여부, CA 번들 재배포 여부, 실제 배포 산출물을 확인한다. 분류 결과만으로 이 질문에 답할 수 없다.
2. 실제 환경의 lockfile을 근거 표의 모든 버전과 대조한다. 선택한 환경을 버전과 해시로 고정하고, 버전이나 extra가 바뀌면 다시 검토한다.
3. 프록시·CA 설정과 `.netrc` 동작을 점검한다. TLS 검증을 유지하고 클라이언트 키 파일은 배포 환경의 비밀 관리 절차로 보호한다.
4. 선택적 PySocks·chardet 의존성을 검토한 뒤 해당 extras를 활성화한다.
5. 운영 도입 결정 전에는 오래된 유지보수·취약점 자료를 갱신한다. 과거 보고서를 번역하는 것은 새 조회가 아니다.
<!-- limitations -->
기존 에이전트 근거 검토 결과는 WARN이다. 등급에 영향을 주는 불일치는 보고되지 않았으나 charset-normalizer 교체의 라이선스 관련 설명, 보안 문서 링크, 리다이렉트 인증 헤더 동작은 재현되지 않았다. 패키지 후보 개수는 15개에서 14개로 수정됐다. 일부 위키 질문과 저장소 목차는 다시 확인하지 않았다.

그래프를 실제 설치 환경과 대조하거나 패키지 배포물에서 독립적으로 재구성하지 않았다. 위키는 Requests 2.34.2에 고정돼 있지 않다. Scorecard는 자료 수집 당시에도 85일 전 결과였다. 이 예제를 만드는 과정에서는 최신 취약점·라이선스를 다시 조회하지 않는다.
