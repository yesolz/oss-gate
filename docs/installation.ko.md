# 설치 안내

[English](installation.md)

## 준비

플러그인·스킬·MCP와 로컬 실행을 지원하는 Claude Code 또는 Codex 클라이언트가 필요합니다. 자신의 계정·요금제로 로그인합니다. OSS Gate 자체에 별도 모델 API 키는 필요하지 않습니다. 다만 웹 전용 채팅, 조직 정책, 로컬 실행 제한, 요금제 한도에 따라 구독이 있어도 사용할 수 없는 환경이 있습니다.

[uv](https://docs.astral.sh/uv/getting-started/installation/)와 Git을 설치합니다. Python 3.10 이상은 uv가 준비할 수 있습니다. 최초 실행 때 고정된 Python 의존성을 내려받고 이후 캐시를 사용합니다. OSS Gate를 위해 Node.js, AWS 계정, jq나 전용 서버를 준비할 필요는 없습니다.

## Claude Code

```sh
claude plugin marketplace add yesolz/oss-gate
claude plugin install oss-gate@oss-gate
```

공개 전 로컬 체크아웃을 시험하려면 저장소에서 `claude plugin marketplace add .`를 실행한 뒤 설치합니다. 한 세션만 불러오려면 `claude --plugin-dir ./plugins/oss-gate`를 사용합니다. 새 세션의 `/mcp`에서 `deepwiki`와 `depsdev`가 모두 연결됐는지 확인합니다. 호출은 `/oss-gate:oss-review`입니다.

삭제는 `claude plugin uninstall oss-gate@oss-gate`, 마켓플레이스까지 제거하려면 `claude plugin marketplace remove oss-gate`입니다. 이미 생성한 검토서는 삭제되지 않습니다.

## Codex

플러그인 CLI를 지원하는 버전:

```sh
codex plugin marketplace add yesolz/oss-gate
codex plugin add oss-gate@oss-gate
codex plugin list --marketplace oss-gate
```

로컬 시험은 `yesolz/oss-gate` 대신 체크아웃의 절대 경로나 저장소 루트에서 `.`을 사용합니다. 목록은 `.agents/plugins/marketplace.json`, 패키지는 `plugin.json`과 `mcp.json`을 사용합니다. 설치 기능이 Plugins 화면에만 있는 버전은 저장소 마켓플레이스를 추가하고 그 화면에서 OSS Gate를 설치합니다.

새 로컬 세션에서 두 MCP 연결을 확인한 뒤 `oss-review` 스킬을 지정해 요청합니다. 호출 방식과 UI 제공 여부는 클라이언트 버전에 따라 다릅니다. 실제 시험 버전은 릴리스 검증 기록에 남깁니다.

삭제는 `codex plugin remove oss-gate@oss-gate`, 마켓플레이스 삭제는 `codex plugin marketplace remove oss-gate`입니다. 워크스페이스의 검토서는 남습니다.

## Codex 수동 설정

플러그인 설치를 지원하지 않는 클라이언트는 체크아웃을 유지하고 두 MCP를 직접 등록할 수 있습니다.

```sh
codex mcp add oss-gate-deepwiki --url https://mcp.deepwiki.com/mcp
codex mcp add oss-gate-depsdev -- uv run --frozen --project /absolute/path/oss-gate/plugins/oss-gate python /absolute/path/oss-gate/plugins/oss-gate/mcp/depsdev/server.py
```

`/absolute/path/oss-gate`는 실제 체크아웃 위치로 바꿉니다. 네 스킬 디렉터리를 지원되는 스킬 위치에 심볼릭 링크로 연결합니다. 예를 들어 `~/.agents/skills/oss-review`가 `<체크아웃>/plugins/oss-gate/skills/oss-review`를 가리키게 합니다. 같은 이름의 기존 스킬을 덮어쓰지 않습니다. 공통 참조와 렌더러 경로를 유지해야 하므로 `SKILL.md`만 복사하면 안 됩니다. 심볼릭 링크를 지원하지 않는 환경은 플러그인 전체를 안정된 위치에 두고 설정합니다.

제거할 때는 직접 추가한 링크와 `codex mcp remove oss-gate-deepwiki`, `codex mcp remove oss-gate-depsdev`만 제거합니다. 다른 클라이언트 설정을 지우지 않습니다.

## 연결과 데이터 흐름

- depsdev는 공개 패키지·버전·저장소 식별자와 선택한 manifest 항목을 `api.deps.dev`, `api.osv.dev`에 보냅니다.
- DeepWiki에는 공개 저장소 이름과 조사 질문이 전달됩니다. 모델 제공자는 해당 클라이언트 약관에 따라 대화·도구 문맥을 처리합니다.
- 수집기는 에이전트가 지정한 폴더에 파일을 씁니다. MCP 서버의 작업 위치와 혼동하지 않도록 워크스페이스 안의 절대 경로를 권장합니다.
- 검토 대상 패키지를 설치하거나 실행하지 않습니다. 에이전트와 uv는 로컬 코드를 실행하므로 호스트의 일반 권한 체계가 적용됩니다. 전역 네트워크 차단 훅을 설치하지 않습니다.
- 비공개 패키지 이름·자격 증명·내부 저장소 내용을 보내지 않습니다. manifest는 조회 전에 확인합니다.

`uv: command not found`는 데스크톱 앱의 PATH에서 uv를 찾지 못하는 경우입니다. 설치 후 앱을 다시 시작하거나 실제 uv 절대 경로를 설정합니다. 의존성 그래프 부재와 위키 미색인은 설치 실패가 아닌 조회 범위의 한계입니다. 시간 초과와 요청 제한도 미확인으로 남겨야 하며 0건으로 바꾸면 안 됩니다.

공식 안내: [Claude 마켓플레이스](https://code.claude.com/docs/en/plugin-marketplaces), [OpenAI 플러그인](https://developers.openai.com/plugins/build/plugins), [Codex MCP](https://developers.openai.com/codex/mcp).
