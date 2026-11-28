"""Deterministic bilingual repository reports rendered from sealed evidence only."""

import json
import os
from pathlib import Path

from .repo_review import SCHEMA
from .render import LABELS, esc, markdown_engine, rendered_tables, shell, verdict_seal
from .snapshot import verify
from .license_display import explain as explain_license
from .policy import advisory_groups

GAPS = {
    "jvm_omitted_nodes": (
        "Maven verbose 트리의 선택 제외 항목은 조회하지 않음",
        "Omitted Maven verbose nodes excluded from queries",
    ),
    "jvm_version_unresolved": ("JVM 동적·SNAPSHOT 버전 미확인", "Dynamic/SNAPSHOT JVM version unverified"),
    "jvm_variant_unverified": ("JVM classifier·artifact 변형 미확인", "JVM classifier/artifact variant unverified"),
    "jvm_local_artifact": ("JVM system 경로 artifact 제외", "JVM system-path artifact excluded"),
    "jvm_manifest_identity_unverified": (
        "Maven POM과 가져온 트리의 프로젝트 일치 미확인",
        "Maven POM/imported tree project identity unverified",
    ),
    "jvm_manifest_missing": (
        "JVM 해결 결과에 연결할 manifest 미확인",
        "JVM resolution has no verified associated manifest",
    ),
    "jvm_dependency_edges_unverified": (
        "Gradle lock에는 직접·간접 연결 정보 없음",
        "Gradle lock does not record direct/transitive edges",
    ),
    "jvm_build_configuration_unverified": (
        "JVM 빌드·프로필·저장소 설정과 결과 최신성 미확인",
        "JVM build/profile/repository configuration and input freshness unverified",
    ),
    "jvm_resolution_invalid": (
        "JVM 해결 결과 형식 오류 또는 처리 한도",
        "Invalid JVM resolution input or resource limit",
    ),
    "jvm_resolved_input_missing": ("Maven JSON 트리 또는 Gradle lock 필요", "Maven JSON tree or Gradle lock required"),
    "swift_source_unverified": (
        "Swift 로컬·registry·비표준 출처 미확인",
        "Swift local, registry or unsupported source unverified",
    ),
    "swift_nonversion_pin": (
        "Swift branch·revision 전용 pin의 버전 미확인",
        "Swift branch/revision-only pin version unverified",
    ),
    "swift_revision_unverified": ("Swift pin의 소스 리비전 미확인", "Swift pin source revision unverified"),
    "swift_manifest_resolution_unverified": (
        "Swift manifest·pin 일치, 직접·간접 연결 및 mirror 설정 미확인",
        "Swift manifest/pin freshness, dependency edges and mirrors unverified",
    ),
    "swift_resolution_invalid": (
        "Swift Package.resolved 오류 또는 미지원 형식",
        "Invalid or unsupported Swift Package.resolved",
    ),
    "swift_resolved_input_missing": ("Swift Package.resolved 필요", "Swift Package.resolved required"),
    "swift_license_source_unavailable": (
        "Swift 라이선스 메타데이터 공급원 미지원",
        "Swift license metadata source not supported",
    ),
    "swift_advisory_aliases_unverified": (
        "SwiftURL 정규 저장소 이름과 다른 취약점 별칭은 미확인",
        "Swift advisories under noncanonical package aliases may not match",
    ),
    "container_reference_unresolved": (
        "컨테이너 이미지 변수·선언을 해석하지 못함",
        "Unresolved container image variable or declaration",
    ),
    "container_final_image_unverified": ("Docker 빌드의 최종 이미지 미검사", "Final Docker build image not scanned"),
    "container_input_invalid": (
        "컨테이너 입력 오류·미지원 형식 또는 처리 한도",
        "Invalid/unsupported container input or resource limit",
    ),
    "container_scan_missing": ("이미지 digest와 일치하는 검사 결과 없음", "No scan matched to the exact image digest"),
    "container_digest_unverified": (
        "가져온 검사 결과의 이미지 manifest digest 미확인",
        "Imported scan image manifest digest unverified",
    ),
    "container_scan_coverage_unverified": (
        "가져온 스캐너 결과의 최신성·필터·전체 검사 범위 미확인",
        "Imported scanner freshness, filters and complete coverage unverified",
    ),
    "container_suppressed_findings": (
        "스캐너에서 억제된 항목도 함께 심사함",
        "Scanner-suppressed findings retained in review",
    ),
    "container_licenses_unverified": (
        "컨테이너 전체 구성요소의 라이선스 미확인",
        "Licenses of all container components unverified",
    ),
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


def version_basis(package, ko):
    if package["system"] == "go":
        return "선언" if ko else "Declared"
    if any(o.get("basis") == "resolved_tree" for o in package["occurrences"]):
        return "해결 트리" if ko else "Resolved tree"
    return "잠금" if ko else "Locked"


def container_section(data, lang):
    ko = lang == "ko"
    scans = data["verdict"].get("container_scans", [])
    images = data["inventory"].get("container_images", [])
    if not scans and not images:
        return []
    lines = [
        "",
        "## " + ("컨테이너 검사 가져오기" if ko else "Imported container scans"),
        "",
        (
            "아래 건수는 가져온 결과에 기록된 항목 수입니다. 온라인 패키지 검사율과 별개이며, 0건은 전체 검사 완료나 취약점 부재를 뜻하지 않습니다. 태그 이름만으로는 검사 결과를 연결하지 않습니다."
            if ko
            else "Counts below describe imported records, separately from online package queries. Zero findings do not establish complete coverage or absence of vulnerabilities. Tags alone do not bind a scan to an image."
        ),
        "",
    ]
    if images:
        lines.extend(
            [
                md_table(
                    ["선언 파일", "이미지", "역할", "digest 일치 보고서"]
                    if ko
                    else ["Declaration", "Image", "Role", "Digest-matched reports"],
                    [[p["source"], p["reference"], p["role"], ", ".join(p["matched_reports"]) or "?"] for p in images],
                ),
                "",
            ]
        )
    for scan in scans:
        lines.extend(
            [
                "### " + cell(scan["source"]),
                "",
                md_table(
                    ["항목", "값"] if ko else ["Field", "Value"],
                    [
                        ["스캐너" if ko else "Scanner", scan["scanner"] + " " + (scan["scanner_version"] or "?")],
                        ["판정" if ko else "Verdict", LABELS[lang][scan["overall"]]],
                        ["이미지 digest" if ko else "Image digest", ", ".join(scan["references"]) or "?"],
                        ["입력 SHA-256" if ko else "Input SHA-256", scan.get("input_sha256") or "?"],
                        ["기록된 검사 시각" if ko else "Recorded scan time", scan["created_at"] or "?"],
                        ["가져온 패키지 항목" if ko else "Imported package records", len(scan["packages"])],
                        ["가져온 취약점 항목" if ko else "Imported findings", len(scan["findings"])],
                        ["보존된 억제 항목" if ko else "Suppressed records retained", scan["ignored_count"]],
                    ],
                ),
                "",
                md_table(
                    ["출처", "패키지·버전", "취약점", "심각도", "점수", "수정 버전", "억제 여부"]
                    if ko
                    else [
                        "Namespace",
                        "Package version",
                        "Advisory",
                        "Severity",
                        "Score",
                        "Fixed versions",
                        "Suppressed",
                    ],
                    [
                        [
                            f["namespace"],
                            f["name"] + "@" + f["version"],
                            f["id"],
                            f["severity"],
                            f["score"],
                            ", ".join(f["fixed_versions"]) or "?",
                            f["suppressed"],
                        ]
                        for f in scan["findings"]
                    ],
                ),
                "",
            ]
        )
        if scan["packages"]:
            lines.extend(
                [
                    md_table(
                        ["구성요소", "라이선스", "라이선스·추가 정책", "미확인·정책 사유"]
                        if ko
                        else ["Component", "Licenses", "License/additional policy", "Gaps/policy reasons"],
                        [
                            [
                                p["namespace"] + ":" + p["name"] + "@" + p["version"],
                                ", ".join(p["licenses"] or []) or "?",
                                LABELS[lang][p["verdict"]["overall"]],
                                ", ".join(
                                    [
                                        *(GAPS.get(g, (g, g))[0 if ko else 1] for g in p["verdict"]["coverage_gaps"]),
                                        *(LABELS[lang].get(f["code"], f["code"]) for f in p["verdict"]["findings"]),
                                    ]
                                ),
                            ]
                            for p in scan["packages"]
                        ],
                    ),
                    "",
                ]
            )
    return lines


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
            "Yarn·Cargo·Gradle·Swift 잠금 목록, Maven 해결 트리와 Go 선언 버전의 취약점·라이선스를 심사합니다. 컨테이너는 가져온 Trivy·Grype 이미지 검사 결과를 별도로 평가합니다. 빌드 설정·최신성·배포 도달 가능성·소스코드·유지보수는 미확인일 수 있습니다. 미확인 항목과 버전 기준을 함께 확인하세요."
            if ko
            else "This verdict screens Yarn/Cargo/Gradle/Swift lock inventories, Maven resolved trees and Go declarations. Imported Trivy/Grype image findings are evaluated separately. Build configuration, freshness, deployment reachability, source code and maintenance may remain unverified. Read the coverage gaps and version basis with the findings."
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
                ["가져온 컨테이너 보고서" if ko else "Imported container reports", s.get("container_reports", 0)],
                [
                    "가져온 컨테이너 취약점 항목" if ko else "Imported container findings",
                    s.get("container_imported_findings", 0),
                ],
                ["미확인 항목" if ko else "Coverage gaps", s["coverage_gaps"]],
            ],
        ),
        "",
        (
            "분모는 식별된 생태계·패키지·버전 수입니다. 컨테이너 가져오기·미지원 파일·해석하지 못한 의존성은 이 수에 포함되지 않습니다. 메타데이터 확보는 라이선스 허용 판정과 다릅니다."
            if ko
            else "Denominators count identified ecosystem/package versions. Container imports, unsupported files and unresolved dependencies are outside these totals. Available license metadata does not mean the license is allowed."
        ),
        "",
        "## " + ("조치 순서" if ko else "Next actions"),
        "",
    ]
    blocked = [p for p in verdict["packages"] if p["verdict"]["overall"] == "hold"]
    held_scans = [s for s in verdict.get("container_scans", []) if s["overall"] == "hold"]
    if held_scans:
        lines.append(
            "보류된 컨테이너의 구성요소·수정 버전·라이선스를 확인하고, 변경 후 최종 이미지 digest를 다시 검사하세요."
            if ko
            else "Review components, fixed versions and licenses in held container scans, then rescan the final image digest after changes."
        )
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
    if not blocked and not held_scans and not verdict["coverage_gaps"]:
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
    lines.extend(
        [
            "Gradle·Swift 잠금 파일과 컨테이너 결과만으로는 직접 의존성을 확정하지 않습니다. 아래 표의 누락은 의존성 부재를 뜻하지 않습니다."
            if ko
            else "Gradle/Swift locks and container scans do not establish direct dependencies. Missing rows below do not mean dependencies are absent.",
            "",
        ]
    )
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
                version_basis(p, ko),
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
    lines.extend(container_section(data, lang))
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


def report_body(text):
    """Attach deterministic heading destinations before building the contents links."""
    md, env = markdown_engine(), {}
    tokens = md.parse(text, env)
    sections = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag == "h2":
            target = f"repository-section-{len(sections) + 1}"
            token.attrSet("id", target)
            # Inline text has already passed the safe Markdown tokenizer.
            label = tokens[index + 1].content
            sections.append((target, label))
    return rendered_tables(md.renderer.render(tokens, md.options, env)), sections


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
        body, sections = report_body(text)
        title = "레포 의존성 심사" if lang == "ko" else "Repository dependency review"
        contents = "목차" if lang == "ko" else "Contents"
        available = [code for code in ("ko", "en") if code in languages or (folder / f"report.{code}.html").is_file()]
        language_nav = (
            '<nav class="language" aria-label="Language">'
            + " ".join(
                f'<a href="report.{code}.html" lang="{code}" {"aria-current=page" if code == lang else ""}>{"한국어" if code == "ko" else "English"}</a>'
                for code in available
            )
            + "</nav>"
        )
        toc = (
            f'<nav class="toc repository-toc" aria-label="{contents}"><ol>'
            + "".join(f'<li><a href="#{target}">{esc(label)}</a></li>' for target, label in sections)
            + "</ol></nav>"
        )
        cover = (
            f'<a class="brand" href="#main"><span class="wordmark">OSS GATE</span><span class="brand-sub">{title}</span></a>'
            + language_nav
            + verdict_seal(grade, lang, str(data["generated_at"])[:10])
            + f'<details class="details grade-guide"><summary>{t["grades"]}</summary><p>{t["grade_help"]}</p></details>'
            + toc
            + f'<div class="actions"><button data-print>{esc(t["print"])}</button><a href="review.{lang}.md" download>{esc(t["markdown"])}</a>'
            + f'<a href="data.json" download>{esc(t["snapshot"])}</a><a href="api-responses.json" download>API JSON</a></div>'
        )
        content = shell(
            data["inventory"]["name"],
            lang,
            cover,
            '<article class="review-body repository-report">' + body + "</article>",
            cover_class="repository-cover",
        ).replace(
            "</head>",
            "<style>.repository-report th{white-space:nowrap}.repository-report td:first-child{min-width:130px}.repository-report td{overflow-wrap:break-word}.repository-toc{max-height:32vh;overflow-y:auto}.cover .repository-toc a{padding:4px 0 4px 12px}@media(min-width:1001px){.repository-cover .cover-in{max-height:calc(100vh - 64px);overflow-y:auto}}@media print{.repository-cover .cover-in{max-height:none;overflow:visible}}</style></head>",
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
