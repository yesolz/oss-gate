"""Rebuild bilingual examples from immutable historical data and reviewed narratives."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/oss-gate"))
from core.policy import evaluate, advisory_groups
from core.licenses import classify_license
from core.render import main, LABELS
from core.snapshot import sha256


def md_table(headers, rows):
    def cell(v):
        return str(v if v is not None else "?").replace("|", "\\|").replace("\n", " ")

    return "\n".join(
        ["| " + " | ".join(map(cell, headers)) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
        + ["| " + " | ".join(map(cell, row)) + " |" for row in rows]
    )


def narratives(name, lang):
    text = (ROOT / f"examples/narratives/{name}.{lang}.md").read_text(encoding="utf-8")
    pieces = re.split(r"<!-- (\w+) -->\n", text)
    return {pieces[i]: pieces[i + 1].strip() for i in range(1, len(pieces), 2)}


def build_review(folder):
    data = json.loads((folder / "data.json").read_text(encoding="utf-8"))
    target, gd, lp = data["target"], data["get_dependencies"], data["lookup_package"]
    verdict = evaluate(data)
    original_hash = sha256(folder / "data.json")
    for lang in ("ko", "en"):
        t = LABELS[lang]
        ko = lang == "ko"
        n = narratives(target["name"], lang)
        heading = (
            [
                "판정과 범위",
                "이 소프트웨어는 무엇인가",
                "외부 통신과 설정",
                "라이선스 검토",
                "알려진 취약점",
                "의존성",
                "유지보수",
                "도입 조치",
                "확인하지 못한 것",
                "근거와 검증",
            ]
            if ko
            else [
                "Decision and scope",
                "What the software does",
                "External communication and configuration",
                "License review",
                "Known vulnerabilities",
                "Dependencies",
                "Maintenance",
                "Adoption actions",
                "Unknowns and limitations",
                "Evidence and verification",
            ]
        )
        blocks = [
            f"# {target['name']} {target['version']}: {t['title']}",
            f"{t['date']}: {data['generated_at']} · {target['system']} · {target.get('repo')} · {verdict['policy']}",
            f"> {t['historical']}",
            f"**{t['verdict']}: {t[verdict['overall']]}**",
            n["summary"],
        ]

        def section(i, text):
            blocks.extend([f"## {i}. {heading[i - 1]}", text])

        section(
            1,
            md_table(["영역" if ko else "Area", t["verdict"]], [[t[a], t[g]] for a, g in verdict["areas"].items()])
            + "\n\n"
            + t["notice"]
            + "\n\n"
            + ("과거 판정" if ko else "Historical verdict")
            + f": `{t.get({'가능': 'allow', '조건부': 'conditional', '보류': 'hold'}.get(data['verdict']['overall'], 'unknown'))}`. "
            + (
                "현재 표는 동일한 저장 자료에 정책 v2를 적용한 결과다."
                if ko
                else "The table above applies policy v2 to the same saved evidence."
            ),
        )
        section(2, n["overview"])
        section(3, n["communication"])
        nodes = [x for x in gd.get("nodes", []) if x.get("relation") != "SELF"]
        lic_intro = f"`{target['name']}@{target['version']}`: " + ", ".join(lp.get("licenses", [])) + ".\n\n"
        lic_intro += (
            "분류는 법적 판단이 아니다. `unknown`은 자동 승인하지 않는 항목이며, 메타데이터 누락·미지원 식별자·미해석 예외를 포함한다. 여러 라이선스의 관계가 명시되지 않은 목록은 보수적으로 AND처럼 검토한다. OR 선택지는 선택·적용 근거를 기록해야 한다."
            if ko
            else "Categories are screening outcomes, not legal conclusions. `unknown` includes missing metadata, unsupported identifiers and uninterpreted exceptions. A list with an unspecified relationship is conservatively reviewed as AND; an OR choice must be selected and documented."
        )
        lic_intro += "\n\n" + md_table(
            [t["package"], t["version"], t["license"], "Category", t["path"]],
            [
                [
                    x.get("name"),
                    x.get("version"),
                    ", ".join(x.get("licenses") or []) or t["missing"],
                    classify_license(x.get("licenses"))["category"],
                    " → ".join(x.get("path") or []),
                ]
                for x in nodes
            ],
        )
        if gd.get("fallback_used"):
            lic_intro += "\n\n**" + t["fallback"] + "**"
        section(4, lic_intro)
        groups = advisory_groups(data.get("advisories"))
        vuln = (
            md_table(
                ["ID", t["score"], "Aliases", t["details"]],
                [
                    [
                        g["id"],
                        g["score"] if g["score"] is not None else t["missing"],
                        ", ".join(g["aliases"]),
                        g["title"],
                    ]
                    for g in groups
                ],
            )
            if groups
            else t["no_vulns"]
        )
        vuln += "\n\n" + (
            "별칭이 연결된 권고는 한 묶음으로 집계한다. 제목은 출처 원문이다. 점수 미상은 0점으로 바꾸지 않는다. 수정 버전 목록은 패키지·버전 분기를 대조하기 전에는 업그레이드 권고가 아니다."
            if ko
            else "Connected aliases count as one group. Titles are source text. Missing severity is not a zero score. A list of fixed versions is not an upgrade recommendation until the affected package and branch have been matched."
        )
        section(5, vuln)
        counts = gd.get("counts", {})
        dep = (
            f"{t['direct']}: {counts.get('direct', '?')} · {t['indirect']}: {counts.get('indirect', '?')} · graph version: `{gd.get('resolved_version') or gd.get('version')}`\n\n"
            + n["roles"]
        )
        dep += "\n\n" + md_table(["Parent", "Child"], gd.get("edges_named", []))
        section(6, dep)
        sc = (data.get("get_project") or {}).get("scorecard") or {}
        maint = n["maintenance"]
        if sc:
            maint += "\n\n" + md_table(
                ["Check", t["score"], t["details"]],
                [[c.get("name"), c.get("score"), c.get("reason")] for c in sc.get("checks", [])],
            )
        section(7, maint)
        section(8, n["actions"])
        gaps = ", ".join(verdict["coverage_gaps"]) or (
            "자동 점검상 추가 플래그 없음. 아래 서술의 한계는 별도로 남아 있다."
            if ko
            else "No additional machine coverage flag. Narrative limitations below still apply."
        )
        section(9, f"{t['coverage']}: {gaps}\n\n" + n["limitations"])
        sources = [
            [t["license"], "data.json#/lookup_package/licenses"],
            [t["deps"], "data.json#/get_dependencies"],
            [t["vulns"], "data.json#/advisories"],
            [t["maintenance"], "data.json#/get_project/scorecard"],
            ["DeepWiki", "data.json#/deepwiki" if data.get("deepwiki") else "Unavailable in the historical JSON"],
        ]
        evidence = md_table(["주장" if ko else "Claim", "출처" if ko else "Source"], sources)
        evidence += "\n\n" + (
            "검증 상태: **WARN**. 원본 JSON 해시와 정책 재계산·언어별 수치 표를 확인했다. 과거 외부 응답의 진위와 위키 서술 전체를 새로 확인한 것은 아니다."
            if ko
            else "Verification status: **WARN**. The original JSON hash, policy calculation and bilingual numerical tables are checked. This does not freshly authenticate the old external responses or verify every wiki assertion."
        )
        evidence += (
            f"\n\nSHA-256 (`data.json`): `{original_hash}`\n\n[deps.dev](https://deps.dev/) · [OSV](https://osv.dev/) · [DeepWiki](https://deepwiki.com/{target.get('repo')})\n\n"
            + (
                "출처·이용 조건은 [NOTICE](../../NOTICE.md)를 참고한다."
                if ko
                else "See [NOTICE](../../NOTICE.md) for source attribution and terms."
            )
        )
        section(10, evidence)
        (folder / f"review.{lang}.md").write_text("\n\n".join(blocks) + "\n", encoding="utf-8", newline="\n")
    (folder / "verification.json").write_text(
        json.dumps(
            {
                "status": "WARN",
                "scope": "Historical snapshot integrity and policy re-evaluation; no fresh source authentication",
                "source_sha256": original_hash,
                "policy": verdict["policy"],
                "original_reviewer": data["verdict"].get("reviewer"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    main([str(folder), "--language", "both"])
    (folder / "review.md").write_text(
        "[한국어 검토서](review.ko.md) · [English review](review.en.md)\n", encoding="utf-8", newline="\n"
    )
    (folder / "report.html").write_text(
        '<!doctype html><html lang="ko"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=report.ko.html"><title>OSS Gate</title><a href="report.ko.html">한국어</a> · <a href="report.en.html">English</a></html>\n',
        encoding="utf-8",
        newline="\n",
    )
    assert sha256(folder / "data.json") == original_hash


if __name__ == "__main__":
    for folder in sorted((ROOT / "examples/reviews").iterdir()):
        if folder.is_dir():
            build_review(folder)
    for kind in ("periodic", "proposals"):
        for source in sorted((ROOT / "examples" / kind).glob("*.md")):
            lang = source.stem.rsplit(".", 1)[-1]
            if lang in ("ko", "en"):
                main([str(source), "--document", "--language", lang, "--out", str(source.with_suffix(".html"))])
