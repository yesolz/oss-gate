"""Deterministic bilingual repository reports rendered from sealed evidence only."""

import json
import os
from pathlib import Path

from .repo_review import SCHEMA
from .render import LABELS, esc, markdown, shell
from .snapshot import verify
from .license_display import explain as explain_license
from .policy import advisory_groups

GAPS = {
    "go_manifest_invalid": ("Go 선언 형식 오류 또는 미지원 구문", "Invalid or unsupported Go declarations"),
    "go_workspace_member_missing": (
        "Go workspace 모듈 누락 또는 외부 경로",
        "Go workspace module missing or outside inventory",
    ),
    "go_workspace_conflict": (
        "Go workspace 대체 규칙 또는 범위 충돌",
        "Conflicting Go workspace replacements or scope",
    ),
    "go_build_list_unverified": (
        "Go 선언 버전만 확인: 실제 빌드 선택 버전·전체 그래프 미확인",
        "Go requirements only: selected build versions and complete graph unverified",
    ),
    "go_requirement_unresolved": (
        "Go 제외 버전 또는 충돌한 대체 규칙",
        "Excluded Go version or conflicting replacement",
    ),
    "go_local_replacement": (
        "Go 로컬 대체 코드의 버전·출처 미확인",
        "Go local replacement version and source unverified",
    ),
    "cargo_manifest_invalid": ("Cargo manifest 형식 오류", "Invalid Cargo manifest"),
    "cargo_lock_invalid": (
        "Cargo lockfile 형식·버전 오류 또는 처리 한도",
        "Invalid/unsupported Cargo lockfile or resource limit",
    ),
    "cargo_manifest_unassigned": (
        "Cargo manifest에 연결할 lockfile·workspace 미확인",
        "Cargo manifest has no verified lockfile/workspace association",
    ),
    "cargo_source_unverified": (
        "Cargo Git·대체 레지스트리·교체 출처 미확인",
        "Cargo Git, alternate registry or replacement source unverified",
    ),
    "cargo_root_manifest_missing": ("Cargo lockfile의 루트 manifest 누락", "Cargo lockfile root manifest missing"),
    "cargo_workspace_member_missing": ("Cargo workspace 멤버 누락", "Cargo workspace member missing"),
    "cargo_inheritance_unresolved": ("Cargo workspace 상속 해석 실패", "Cargo workspace inheritance unresolved"),
    "cargo_local_dependency_unverified": (
        "Cargo 로컬 의존성의 manifest·연결 미확인",
        "Cargo local dependency manifest or association unverified",
    ),
    "cargo_requirement_unverified": (
        "Cargo 버전 조건과 lockfile의 일치 미확인",
        "Cargo requirement compatibility with lockfile unverified",
    ),
    "unsupported_format": ("아직 지원하지 않는 의존성 파일", "Dependency format not yet supported"),
    "file_unreadable_or_limited": ("파일을 읽지 못했거나 크기 제한 초과", "Unreadable file or resource limit"),
    "directory_unreadable": ("디렉터리를 읽지 못함", "Unreadable directory"),
    "symlink_skipped": ("심볼릭 링크 검사 제외", "Symbolic link not followed"),
    "discovery_limit": ("레포 탐색 한도 도달", "Repository discovery limit reached"),
    "invalid_manifest": ("잘못된 manifest 형식", "Invalid manifest"),
    "lockfile_missing": ("연결할 Yarn lockfile 없음", "No associated Yarn lockfile"),
    "lockfile_invalid_or_unsupported": (
        "Yarn lockfile 형식 오류 또는 미지원 버전",
        "Invalid or unsupported Yarn lockfile",
    ),
    "no_supported_projects": ("지원하는 프로젝트를 찾지 못함", "No supported projects found"),
    "unsupported_dependency_source": (
        "npm 이외의 출처: 수정·Git·로컬 의존성 등",
        "Non-npm source: patched, Git or local dependency",
    ),
    "root_workspace_missing": ("lockfile의 루트 workspace 누락", "Root workspace missing in lockfile"),
    "manifest_not_in_lock": ("lockfile에 없는 manifest", "Manifest not represented in lockfile"),
    "workspace_not_declared": ("루트에서 선언하지 않은 workspace", "Workspace not declared by root"),
    "invalid_workspace_patterns": ("workspace 선언 형식 오류", "Invalid workspace declaration"),
    "unsupported_workspace_pattern": ("지원하지 않는 workspace 패턴", "Unsupported workspace pattern"),
    "workspace_manifest_missing": ("workspace의 package.json 누락", "Workspace manifest missing"),
    "workspace_name_mismatch": ("manifest와 workspace 이름 불일치", "Manifest and workspace name mismatch"),
    "package_manager_mismatch": (
        "선택한 패키지 매니저가 Yarn Berry와 다름",
        "Selected package manager differs from Yarn Berry",
    ),
    "manifest_lock_mismatch": ("manifest와 lockfile의 의존성 불일치", "Manifest and lock dependency mismatch"),
    "stale_workspace_dependencies": ("manifest에서 제거된 의존성이 lockfile에 남음", "Stale workspace dependencies"),
    "invalid_manifest_dependencies": ("의존성 선언 형식 오류", "Invalid dependency declarations"),
    "invalid_manifest_dependency": ("의존성 이름 또는 버전 선언 오류", "Invalid dependency name or declaration"),
    "lock_version_mismatch": ("lockfile 내부 버전 불일치", "Conflicting versions inside lockfile"),
    "unresolved_lock_edge": ("의존성 연결을 해석하지 못함", "Unresolved lock dependency edge"),
    "peer_bindings_unverified": ("peer 의존성의 실제 연결 미확인", "Installed peer dependency bindings unverified"),
    "unattributed_lock_entry": ("사용 프로젝트를 연결하지 못한 lock 항목", "Lock entry not attributed to a project"),
    "package_policy_blocked": ("선택 정책으로 패키지 조회 차단", "Package query blocked by selected policy"),
    "packages_unqueried": ("정책 또는 조회 한도로 미조회 패키지 존재", "Packages unqueried due to policy or query cap"),
    "advisory_limit": ("취약점 상세 조회 한도 도달", "Advisory detail limit reached"),
    "vulnerability_query_incomplete": ("취약점 조회 미완료", "Vulnerability query incomplete"),
    "license_query_incomplete": ("라이선스 메타데이터 조회 미완료", "License metadata query incomplete"),
    "license_unverified": ("라이선스를 확인하지 못함", "License unverified"),
    "advisory_details_incomplete": ("취약점 상세 근거 불완전", "Advisory details incomplete"),
    "no_queryable_packages": ("심사할 공개 패키지 목록 없음", "No queryable public package inventory"),
    "release_time_unverified": ("릴리스 시각 미확인", "Release timestamp unverified"),
    "communication_unverified": ("외부 통신 검토 미확인", "Communication review unverified"),
    "policy_limited_collection": ("선택 정책으로 근거 수집 제한", "Evidence collection limited by policy"),
}


def cell(value):
    text = str(value if value is not None else "?").replace("\n", " ").replace("\r", " ")
    for char in "\\`*_{}[]<>()#+.!|":
        text = text.replace(char, "\\" + char)
    return text


def md_table(headers, rows):
    return "\n".join(
        [
            "| " + " | ".join(cell(v) for v in headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *("| " + " | ".join(cell(v) for v in row) + " |" for row in rows),
        ]
    )


def gap_target(gap):
    parts = [gap[k] for k in ("source", "path", "dependency", "source_type") if gap.get(k)]
    package = gap.get("package")
    if isinstance(package, dict):
        parts.append(f"{package['system']}:{package['name']}@{package['version']}")
    elif package:
        parts.append(str(package))
    return " / ".join(parts) or "."


def narrative(data, lang):
    ko = lang == "ko"
    t, verdict = LABELS[lang], data["verdict"]
    s = verdict["summary"]
    inventory = data["inventory"]
    title = "레포 의존성 심사" if ko else "Repository dependency review"
    lines = [
        f"# {title}: {cell(inventory['name'])}",
        "",
        f"**{t['verdict']}: {t[verdict['overall']]}**",
        "",
        ("수집 시각: " if ko else "Collected at: ") + cell(data["generated_at"]),
        "",
        (
            "Yarn Berry의 npm·Cargo의 crates.io 잠금 버전과 Go 선언 버전의 취약점·라이선스를 심사합니다. 개발·선택·플랫폼별 의존성을 포함합니다. Go의 실제 빌드 선택 버전, 설치·배포 목록, 소스코드·유지보수, 외부 패키지 매니저 설정은 미확인입니다. 패치·Git·로컬 출처와 peer 연결도 별도 확인이 필요합니다."
            if ko
            else "This verdict screens Yarn Berry npm and Cargo crates.io locked versions, plus Go declared versions. It includes development, optional and target-specific entries. Go build selection, installed/deployed artifacts, source code, maintenance and external package-manager configuration remain unverified. Patches, Git/local sources and peer bindings need separate verification."
        ),
        "",
        "## " + ("검사 범위" if ko else "Coverage"),
        "",
        md_table(
            ["항목", "결과"] if ko else ["Measure", "Result"],
            [
                ["프로젝트" if ko else "Projects", s["projects"]],
                ["고유 생태계·패키지·버전" if ko else "Unique ecosystem/package versions", s["packages"]],
                [
                    "취약점 조회 완료" if ko else "Complete vulnerability queries",
                    f"{s['vulnerability_queries_complete']} / {s['packages']}",
                ],
                [
                    "라이선스 메타데이터 확보" if ko else "License metadata available",
                    f"{s['license_metadata_available']} / {s['packages']}",
                ],
                ["영향받는 패키지·버전" if ko else "Affected package versions", s["affected_packages"]],
                ["고유 취약점 묶음" if ko else "Unique advisory groups", s["advisory_groups"]],
                ["미확인 항목" if ko else "Coverage gaps", s["coverage_gaps"]],
            ],
        ),
        "",
        (
            "분모는 식별된 생태계·패키지·버전 수입니다. 미지원 파일과 해석하지 못한 의존성은 이 수에 포함되지 않습니다. 메타데이터 확보는 라이선스 허용 판정과 다릅니다."
            if ko
            else "Denominators count identified ecosystem/package versions. Unsupported files and unresolved dependencies are outside these totals. Available license metadata does not mean the license is allowed."
        ),
        "",
        "## " + ("조치 순서" if ko else "Next actions"),
        "",
    ]
    blocked = [p for p in verdict["packages"] if p["verdict"]["overall"] == "hold"]
    if blocked:
        lines.append(
            (
                "먼저 보류된 패키지의 취약점·라이선스 근거를 확인하세요. 간접 의존성은 아래 사용 위치와 직접 의존성 목록에서 변경할 상위 패키지를 확인하세요."
                if ko
                else "Review vulnerability and license evidence for held packages first. For transitive dependencies, use the project locations and direct dependency list below to investigate the parent to change."
            )
        )
    if verdict["coverage_gaps"]:
        lines.append(
            (
                "미확인 항목을 해결하고 다시 심사하세요. 누락된 lockfile과 불일치한 선언은 프로젝트의 정상 개발 절차로 갱신해야 합니다."
                if ko
                else "Resolve coverage gaps and run a new review. Update missing or inconsistent lockfiles through the project's normal development workflow."
            )
        )
    if not blocked and not verdict["coverage_gaps"]:
        lines.append(
            t["no_vulns"]
            if not s["affected_packages"]
            else (
                "아래 취약점과 조건부 라이선스의 후속 조치를 검토하세요."
                if ko
                else "Review follow-up actions for advisories and conditional licenses below."
            )
        )
    lines.extend(["", "## " + ("프로젝트별 직접 의존성" if ko else "Direct dependencies by project"), ""])
    lines.append(
        md_table(
            ["프로젝트", "의존성", "그룹", "선언 이름"] if ko else ["Project", "Dependency", "Group", "Declared name"],
            [
                [p["path"], f"{d['system']}:{d['name']}@{d['version']}", d["group"], d["declared_name"]]
                for p in inventory["projects"]
                for d in p["direct_dependencies"]
            ],
        )
    )
    lines.extend(["", "## " + ("패키지별 결과" if ko else "Package results"), ""])
    results = {(p["system"], p["name"], p["version"]): p["verdict"] for p in verdict["packages"]}
    rows = []
    for p in data["packages"]:
        v = results[p["system"], p["name"], p["version"]]
        uses = sorted({project for occurrence in p["occurrences"] for project in occurrence["projects"]})
        licenses = p["metadata"]["licenses"]
        license_text = (
            ", ".join(licenses) if isinstance(licenses, list) and all(isinstance(x, str) for x in licenses) else "?"
        )
        ids = sorted(set((p["osv"]["ids"] or []) + p["metadata"]["advisories"]))
        group_count = len(advisory_groups({aid: data["advisories"].get(aid, {}) for aid in ids}))
        rows.append(
            [
                f"{p['system']}:{p['name']}@{p['version']}",
                ("선언" if ko else "Declared") if p["system"] == "go" else ("잠금" if ko else "Locked"),
                t[v["overall"]],
                license_text,
                str(group_count) if p["osv"]["complete"] else (f"≥ {group_count}" if ids else "?"),
                ", ".join(uses) or "?",
            ]
        )
    lines.append(
        md_table(
            ["패키지·버전", "버전 기준", "판정", "라이선스", "취약점 묶음", "사용 프로젝트"]
            if ko
            else ["Package version", "Version basis", "Verdict", "Licenses", "Advisory groups", "Projects"],
            rows,
        )
    )
    lines.extend(["", "## " + ("라이선스 후속 조치" if ko else "License follow-up"), ""])
    lines.append(
        md_table(
            ["패키지", "라이선스 판정", "확인할 내용"] if ko else ["Package", "License verdict", "Action"],
            [
                [
                    f"{p['system']}:{p['name']}@{p['version']}",
                    t[item["assessment"]["tier"]],
                    explain_license(item["assessment"], lang),
                ]
                for p in verdict["packages"]
                for item in p["verdict"]["license_reviews"]
            ],
        )
    )
    policy_findings = [
        [
            f"{p['system']}:{p['name']}@{p['version']}",
            t.get(f.get("outcome"), f.get("outcome", "?")),
            t.get(f["code"], f["code"]),
        ]
        for p in verdict["packages"]
        for f in p["verdict"]["findings"]
        if f.get("area") != "vulns"
    ]
    if policy_findings:
        lines.extend(
            [
                "",
                "## " + ("추가 정책 조치" if ko else "Selected policy actions"),
                "",
                md_table(["패키지", "판정", "사유"] if ko else ["Package", "Verdict", "Reason"], policy_findings),
            ]
        )
    lines.extend(["", "## " + ("취약점 근거" if ko else "Vulnerability evidence"), ""])
    lines.append(
        md_table(
            ["ID", "점수", "요약"] if ko else ["ID", "Score", "Summary"],
            [
                [aid, advisory.get("cvss3_score"), advisory.get("summary") or advisory.get("error") or "?"]
                for aid, advisory in data["advisories"].items()
            ],
        )
    )
    lines.extend(["", "## " + ("미확인 항목" if ko else "Coverage gaps"), ""])
    lines.append(
        md_table(
            ["항목", "대상"] if ko else ["Gap", "Target"],
            [
                [GAPS.get(gap["code"], (gap["code"], gap["code"]))[0 if ko else 1], gap_target(gap)]
                for gap in verdict["coverage_gaps"]
            ],
        )
        if verdict["coverage_gaps"]
        else ("기록된 미확인 항목이 없습니다." if ko else "No recorded coverage gaps.")
    )
    lines.extend(["", "## " + ("발견한 파일" if ko else "Discovered files"), ""])
    lines.append(
        md_table(
            ["파일", "종류", "상태"] if ko else ["File", "Format", "Status"],
            [[f["path"], f["format"], f["status"]] for f in inventory["files"]],
        )
    )
    lines.extend(
        [
            "",
            "## " + ("근거와 한계" if ko else "Evidence and limitations"),
            "",
            (
                "입력 파일의 SHA-256, 제외 디렉터리, 조회 제한, 선택 정책과 패키지별 상세 판정은 data.json에 있습니다. API 원문은 api-responses.json에 보존합니다. 입력 소스코드를 업로드하거나 설치·빌드 명령을 실행하지 않습니다."
                if ko
                else "data.json records input file hashes, excluded directories, query limits, selected policy and detailed package verdicts. api-responses.json preserves API responses. Collection does not upload source code or execute installation/build commands."
            ),
            "",
            "[deps.dev](https://docs.deps.dev/api/v3/) · [OSV](https://osv.dev/) · " + cell(verdict["policy"]),
            "",
        ]
    )
    return "\n".join(lines)


def render_repository(source, language="ko"):
    if language not in ("ko", "en", "both"):
        raise ValueError("unsupported language")
    folder = Path(source).resolve()
    manifest = verify(folder)
    if not {"data.json", "api-responses.json"} <= manifest.keys():
        raise ValueError("repository evidence not sealed")
    data = json.loads((folder / "data.json").read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise ValueError("unsupported repository schema")
    languages = ("ko", "en") if language == "both" else (language,)
    files = []
    for lang in languages:
        text = narrative(data, lang)
        t, grade = LABELS[lang], data["verdict"]["overall"]
        cover = (
            '<div class="brand"><span class="wordmark">OSS GATE</span></div>'
            + f'<div class="document-status"><strong>{esc(t[grade])}</strong><p>{esc("레포 의존성 심사" if lang == "ko" else "Repository dependency review")}</p></div>'
            + f'<div class="actions"><button data-print>{esc(t["print"])}</button><a href="review.{lang}.md">Markdown</a>'
            + '<a href="data.json">Evidence JSON</a><a href="api-responses.json">API JSON</a></div>'
        )
        available = [code for code in ("ko", "en") if code in languages or (folder / f"report.{code}.html").is_file()]
        cover += (
            '<nav class="language">'
            + " ".join(
                f'<a href="report.{code}.html" lang="{code}">{"한국어" if code == "ko" else "English"}</a>'
                for code in available
            )
            + "</nav>"
        )
        content = shell(
            data["inventory"]["name"],
            lang,
            cover,
            '<article class="review-body repository-report">' + markdown(text) + "</article>",
        ).replace(
            "</head>",
            "<style>.repository-report th{white-space:nowrap}.repository-report td:first-child{min-width:130px}.repository-report td{overflow-wrap:break-word}</style></head>",
            1,
        )
        for name, value in ((f"review.{lang}.md", text), (f"report.{lang}.html", content)):
            path = folder / name
            if path.is_symlink() or (path.exists() and not path.is_file()):
                raise ValueError("invalid report destination")
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0), 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                out.write(value)
            files.append(str(path))
    return {"folder": str(folder), "files": files, "verdict": data["verdict"]["overall"]}
