"""Offline, bilingual report rendering with escaped data and a shared visual theme."""

from __future__ import annotations
import argparse
import base64
import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from markdown_it import MarkdownIt
from .policy import advisory_groups, evaluate, obj, seq
from .licenses import classify_license
from .snapshot import load_review, sha256

LABELS = {
    "en": {
        "title": "Open-source adoption review",
        "verdict": "Verdict",
        "allow": "Allow",
        "conditional": "Conditional",
        "hold": "Hold",
        "unknown": "Unverified",
        "license": "License",
        "vulns": "Known vulnerabilities",
        "deps": "Dependencies",
        "maintenance": "Maintenance",
        "summary": "At a glance",
        "evidence": "Evidence",
        "narrative": "Adoption review",
        "direct": "Direct",
        "indirect": "Transitive",
        "advisories": "Advisory groups",
        "coverage": "Coverage gaps",
        "print": "Print / PDF",
        "markdown": "Markdown",
        "snapshot": "Evidence JSON",
        "package": "Package",
        "version": "Version",
        "relation": "Relation",
        "path": "Dependency path",
        "score": "Score",
        "date": "Snapshot date",
        "no_vulns": "No known advisories were returned in this snapshot. This is not proof of absence.",
        "missing": "Not measured",
        "limits": "Interpretation and coverage",
        "historical": "Historical example. The source snapshot is preserved; the verdict shown here is reassessed using policy v2. This is not a live scan.",
        "notice": "A screening aid, not a legal opinion or security certification. Public metadata can be incomplete. DeepWiki narratives are AI-generated and may not describe the reviewed version.",
        "policy": "Policy findings",
        "details": "Source details",
        "tree": "Resolved dependency graph",
        "graph_note": "The table below includes every returned node. A registry graph is not a scan of your installed environment.",
        "read": "Read the full review",
        "raw": "Original API responses",
        "fallback": "Graph version differs from the reviewed version. Treat dependency coverage as unverified.",
        "view": "Inspect findings",
        "current": "Automated policy verdict",
        "generic": "Evidence-based document",
        "supplemental": "Supplemental analysis",
        "no_verdict": "No automated verdict",
        "document_note": "Recommendations in this document are separate from an automated package verdict.",
        "decision": "Decision in brief",
        "context": "Review context",
        "appendix": "Data and source details",
        "grades": "How to read the verdict",
        "additional_policy": "Selected review policy",
        "base_verdict": "Base verdict",
        "effective_verdict": "With selected policy",
        "additional_pass": "No additional blocking condition was found under the selected rules.",
        "release_wait": "The selected release waiting period has not elapsed.",
        "release_time_unverified": "The release time is missing, invalid or later than the evaluation time.",
        "communication_unverified": "A complete, attributed communication review for this version is unavailable.",
        "blocked_destination": "Reviewed evidence identifies a prohibited destination used by default or required for operation.",
        "communication_configuration_unverified": "Some activation or disabling conditions for external communication remain unverified.",
        "policy_limited_collection": "The selected outbound policy blocked part of the evidence collection.",
        "communication_source": "Communication findings use explicitly supplied reviewer evidence. They are not an automated network scan.",
        "grade_help": "Allow: meets the screening rules. Conditional: checks or actions remain. Hold: a policy blocker needs resolution. Unverified is an individual area's evidence status. PASS / WARN / FAIL describe the report's evidence check, not approval to adopt.",
    },
    "ko": {
        "title": "오픈소스 도입 검토서",
        "verdict": "판정",
        "allow": "가능",
        "conditional": "조건부",
        "hold": "보류",
        "unknown": "확인 필요",
        "license": "라이선스",
        "vulns": "알려진 취약점",
        "deps": "의존성",
        "maintenance": "유지보수",
        "summary": "한눈에 보기",
        "evidence": "근거 자료",
        "narrative": "도입 검토서",
        "direct": "직접 의존성",
        "indirect": "간접 의존성",
        "advisories": "취약점 권고 묶음",
        "coverage": "미확인 범위",
        "print": "인쇄 / PDF",
        "markdown": "마크다운",
        "snapshot": "근거 JSON",
        "package": "패키지",
        "version": "버전",
        "relation": "관계",
        "path": "의존성 경로",
        "score": "점수",
        "date": "자료 수집일",
        "no_vulns": "이 스냅샷에서 알려진 권고가 반환되지 않았습니다. 취약점이 없다는 보장은 아닙니다.",
        "missing": "미측정",
        "limits": "해석과 조회 범위",
        "historical": "과거 자료로 만든 예제입니다. 원본 스냅샷을 보존하고 정책 v2로 판정을 다시 계산했습니다. 실시간 검사 결과가 아닙니다.",
        "notice": "도입 검토를 돕는 자료이며 법적 판단이나 보안 인증이 아닙니다. 공개 메타데이터는 불완전할 수 있습니다. DeepWiki 설명은 AI 생성 자료이며 검토 버전과 다를 수 있습니다.",
        "policy": "판정 근거",
        "details": "출처 상세",
        "tree": "해석된 의존성 그래프",
        "graph_note": "아래 표는 반환된 모든 노드를 포함합니다. 레지스트리 그래프는 실제 설치 환경의 검사 결과와 다를 수 있습니다.",
        "read": "검토서 전문 읽기",
        "raw": "API 원본 응답",
        "fallback": "의존성 그래프가 다른 버전의 자료입니다. 요청 버전의 의존성은 확인되지 않았습니다.",
        "view": "근거 펼치기",
        "current": "자동 정책 판정",
        "generic": "근거 기반 문서",
        "supplemental": "보완 분석",
        "no_verdict": "자동 판정 없음",
        "document_note": "이 문서의 권고는 자동 패키지 판정과 별도로 작성한 판단입니다.",
        "decision": "결론부터 읽기",
        "context": "검토 정보",
        "appendix": "수치와 상세 근거",
        "grades": "판정 읽는 법",
        "additional_policy": "선택한 검토 정책",
        "base_verdict": "기본 판정",
        "effective_verdict": "추가 정책 적용 후",
        "additional_pass": "선택한 규칙에서 추가로 제한하는 조건은 확인되지 않았습니다.",
        "release_wait": "선택한 신규 버전 대기 기간이 지나지 않았습니다.",
        "release_time_unverified": "발행 시각이 없거나 잘못됐거나 평가 시각보다 나중입니다.",
        "communication_unverified": "이 버전의 외부 통신을 확인한 완전한 검토 자료가 없습니다.",
        "blocked_destination": "검토 자료에 따르면 금지된 목적지로 기본 활성화되거나 필수인 통신이 있습니다.",
        "communication_configuration_unverified": "외부 통신의 활성화 또는 비활성화 조건 중 일부가 확인되지 않았습니다.",
        "policy_limited_collection": "선택한 외부 전송 정책으로 근거 수집의 일부가 차단됐습니다.",
        "communication_source": "외부 통신 판정은 명시적으로 제공한 검토 자료에 근거합니다. 네트워크를 자동 검사한 결과는 아닙니다.",
        "grade_help": "가능: 현재 점검 기준을 통과했습니다. 조건부: 확인하거나 조치할 일이 남았습니다. 보류: 정책상 막는 항목을 해결해야 합니다. 확인 필요는 개별 항목의 근거 상태입니다. PASS / WARN / FAIL은 보고서의 근거 검증 상태이며 도입 승인이 아닙니다.",
    },
}
TOKENS = {"allow": "good", "conditional": "warn", "hold": "serious", "unknown": "neutral"}
SCRIPT = """document.querySelectorAll('[data-print]').forEach(b=>b.addEventListener('click',()=>window.print()));
const printContext = new Set();
window.addEventListener('beforeprint',()=>{
  document.querySelectorAll('details.context:not([open])').forEach(d=>{printContext.add(d);d.open=true;});
});
window.addEventListener('afterprint',()=>{printContext.forEach(d=>d.open=false);printContext.clear();});"""
EXTRA_CSS = """
html{scroll-behavior:smooth}.seal-v{font-size:25px!important}.seal-k{letter-spacing:.1em}
.review-body{font-size:16px;line-height:1.85}.review-body h1{font-size:27px}.review-body h2{font-size:23px;margin:44px 0 16px}.review-body h3{font-size:18px;margin-top:28px}.review-body p{margin:14px 0}
.review-body ul,.review-body ol{padding-left:24px}.review-body li{margin:7px 0}.review-body pre{overflow:auto;padding:18px;background:var(--sheet-2);font:12px/1.7 var(--mono);white-space:pre}.review-body code{overflow-wrap:anywhere}.review-body blockquote{border-left:3px solid var(--accent);padding:8px 18px;margin:20px 0;background:var(--sheet-2)}
.table-wrap{overflow-x:auto;width:100%}table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;vertical-align:top;padding:12px 10px;border-bottom:1px solid var(--rule);overflow-wrap:anywhere}th{overflow-wrap:normal;word-break:normal;font-weight:600;color:var(--ink-2);background:var(--sheet-2)}
.details{border-top:1px solid var(--rule);padding:14px 0}.details summary{cursor:pointer;font-weight:600}.details pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:11px;background:var(--sheet-2);padding:16px;max-height:500px;overflow:auto}
.notice{padding:16px 20px;border-left:3px solid var(--accent);background:var(--sheet-2);font-size:13px;line-height:1.8;margin:20px 0}.coverage{border-left-color:var(--warn)}
.language{display:flex;gap:14px;align-items:center;font:600 12px var(--sans)}.language a[aria-current]{border-bottom:2px solid var(--ink);padding-bottom:4px}.actions{display:flex;gap:10px;flex-wrap:wrap}.actions a,.actions button{font:500 12px var(--sans);border:1px solid var(--rule);background:var(--sheet);padding:9px 12px;cursor:pointer;color:var(--ink);text-decoration:none}
.cover nav a{display:block;padding:8px 0;font-size:13px}.cover .arows a{display:flex;justify-content:space-between;gap:8px;border-bottom:1px solid var(--rule);font-size:12px}.area-label{color:var(--ink-2)}
.node-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin:20px 0}.node{border:1px solid var(--rule);border-top:3px solid var(--accent);padding:16px;font:13px var(--sans);overflow-wrap:anywhere}.node small{display:block;color:var(--ink-2);margin-top:8px}.node.warn{border-top-color:var(--warn)}.node.unknown{border-top-color:var(--muted)}
.meta{font:11px/1.7 var(--mono);color:var(--muted);overflow-wrap:anywhere}.ledger{--cols:4}.fig{padding:16px 10px!important}.fig-val{font:600 30px var(--serif)}.fig-label{font-size:11px;color:var(--ink-2);margin-top:7px}.legend-note{font:12px/1.8 var(--sans);color:var(--ink-2)}
:focus-visible{outline:3px solid var(--accent);outline-offset:4px}a{overflow-wrap:anywhere}summary{min-height:32px}.skip{position:absolute;left:-9999px}.skip:focus{left:16px;top:16px;background:white;padding:12px;z-index:99}
.document-title{font:650 32px/1.45 var(--sans);letter-spacing:-.025em}.document-kind{font:600 13px var(--sans);color:var(--ink-2);margin:0 0 16px}
.document-status{border-left:3px solid var(--axis);padding:4px 0 4px 16px}.document-status strong{font-size:16px}.document-status p,.grade-guide p{font:13px/1.7 var(--sans);color:var(--ink-2);margin:10px 0 0}
.grade-guide{padding:0;border:0}.grade-guide summary{font-size:12px;color:var(--ink-2)}.context{margin-top:24px;color:var(--ink-2)}.context .review-body{font-size:13px}.brief blockquote{border:0;background:none;margin:0;padding:0}.brief p:first-child{margin-top:0}.brief p:last-child{margin-bottom:0}
.appendix-title{margin-top:72px;padding-top:32px;border-top:3px solid var(--rule);font-size:26px}.sec#decision{margin-top:28px;padding-top:28px}.sec#review{margin-top:32px;padding-top:32px}.sec#review>h2{font-size:14px;color:var(--ink-2)}.sec#review .review-body>h2:first-child{margin-top:20px}
@media(max-width:760px){.page{padding:20px 12px 60px}.sheet{padding:24px 20px}.cover-in{display:grid;grid-template-columns:110px minmax(0,1fr);gap:14px 18px}.cover .brand{grid-column:1;grid-row:1}.cover .language{grid-column:2;grid-row:1;justify-content:flex-end}.cover .seal-wrap{grid-column:1;grid-row:2;align-self:center;align-items:center}.cover .seal{--seal:100px!important}.cover .seal-v{font-size:20px!important}.cover .seal-k{font-size:10px}.cover .seal-d{font-size:9px}.cover .seal-cap{font:600 11px/1.5 var(--sans);text-align:center;margin:4px 0}.cover .arows{grid-column:2;grid-row:2;width:100%}.cover .arows a{font-size:11px}.cover .grade-guide{grid-column:1/-1;grid-row:3}.cover .actions{grid-column:1/-1;grid-row:4}.cover .document-status{grid-column:1/-1;grid-row:2}.document-title{font-size:27px}.review-body{font-size:15px}.ledger{grid-template-columns:repeat(2,1fr)}.fig{border-bottom:1px solid var(--rule)}.review-body h1{font-size:24px}.cover nav.toc{display:none}.pkg{font-size:34px}.desc{font-size:16px}}

@media print{.actions,.language,.skip{display:none!important}.cover{position:static}.review-body h2{break-after:avoid}.node,.notice{break-inside:avoid}.table-wrap{overflow:visible}details{display:block}.page{padding:0}.sheet{padding:25px}a{color:inherit;text-decoration:none}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}html{scroll-behavior:auto}}
"""


def esc(value):
    return html.escape("" if value is None else str(value), quote=True)


def safe_url(value):
    if not isinstance(value, str) or re.search(r"[\x00-\x20\x7f]", value):
        return None
    try:
        parsed = urlsplit(value)
        return (
            value
            if parsed.scheme in ("https", "http") and parsed.hostname and not parsed.username and not parsed.password
            else None
        )
    except ValueError:
        return None


def markdown_engine():
    md = MarkdownIt("commonmark", {"html": False, "typographer": False}).enable("table")

    # Reports never fetch remote images. Retain the caption and URL as text.
    def image_rule(tokens, idx, options, env):
        return '<span class="meta">' + esc(tokens[idx].content) + "</span>"

    md.renderer.rules["image"] = image_rule
    return md


def rendered_tables(result):
    return result.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")


def markdown(text):
    return rendered_tables(markdown_engine().render(text))


def narrative_parts(text):
    """Move an existing opening summary forward, preserving every other source block.

    Token boundaries keep fenced headings and nested quotes intact. All fragments
    share the original reference definitions and the same safe Markdown renderer.
    """
    md, env = markdown_engine(), {}
    tokens = md.parse(text, env)
    boundary = next(
        (i for i, t in enumerate(tokens) if t.type == "heading_open" and t.tag == "h2" and t.level == 0), len(tokens)
    )
    intro, rest = tokens[:boundary], tokens[boundary:]
    # The document title is rendered once by the surrounding page header.
    title = ""
    if intro and intro[0].type == "heading_open" and intro[0].tag == "h1":
        title = intro[1].content
        intro = intro[3:]
    # Historical examples start with a bold verdict; current templates use a quote.
    start = next(
        (
            i
            for i, t in enumerate(intro[:-1])
            if t.type == "paragraph_open" and t.level == 0 and intro[i + 1].content.startswith("**")
        ),
        None,
    )
    if start is not None:
        brief, context = intro[start:], intro[:start]
    else:
        start = next((i for i, t in enumerate(intro) if t.type == "blockquote_open" and t.level == 0), None)
        if start is None:
            brief, context = intro, []
        else:
            end = next(
                i + 1
                for i in range(start + 1, len(intro))
                if intro[i].type == "blockquote_close" and intro[i].level == 0
            )
            brief, context = intro[start:end], intro[:start] + intro[end:]

    def fragment(items):
        return rendered_tables(md.renderer.render(items, md.options, env))

    return title, fragment(brief), fragment(context), fragment(rest)


def reading_sections(text, lang):
    title, brief, context, rest = narrative_parts(text)
    t = LABELS[lang]
    body = section("decision", t["decision"], '<div class="review-body brief">' + brief + "</div>") if brief else ""
    if context:
        body += f'<details class="details context"><summary>{t["context"]}</summary><div class="review-body">{context}</div></details>'
    if rest:
        body += section("review", t["narrative"], '<article class="review-body">' + rest + "</article>")
    return title, body


def render_document(text, lang, kind="document"):
    t = LABELS[lang]
    title, reading = reading_sections(text, lang)
    label = t["supplemental"] if kind == "supplemental" else t["generic"]
    cover = (
        f'<div class="brand"><span class="wordmark">OSS GATE</span><span class="brand-sub">{label}</span></div>'
        + f'<div class="document-status"><strong>{t["no_verdict"]}</strong><p>{t["document_note"]}</p></div>'
        + f'<div class="actions"><button data-print>{t["print"]}</button></div>'
    )
    body = (
        f'<header class="doc-head"><p class="document-kind">{label}</p><h1 class="document-title">{esc(title or label)}</h1></header>'
        + reading
    )
    return shell(title or label, lang, cover, body)


def table(headers, rows):
    return (
        '<div class="table-wrap"><table><thead><tr>'
        + "".join(f'<th scope="col">{esc(h)}</th>' for h in headers)
        + "</tr></thead><tbody>"
        + "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in row) + "</tr>" for row in rows)
        + "</tbody></table></div>"
    )


def section(id_, title, body):
    return f'<section class="sec" id="{id_}"><h2>{esc(title)}</h2>{body}</section>'


def details(label, value):
    return f'<details class="details"><summary>{esc(label)}</summary><pre>{esc(json.dumps(value, ensure_ascii=False, indent=2))}</pre></details>'


def shell(title, lang, cover, body):
    script_hash = base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode()
    csp = f"default-src 'none'; style-src 'unsafe-inline'; script-src 'sha256-{script_hash}'; img-src data:; base-uri 'none'; form-action 'none'"
    css = Path(__file__).with_name("theme.css").read_text(encoding="utf-8") + EXTRA_CSS
    return f'''<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="{csp}"><meta name="generator" content="OSS Gate 0.4.2"><title>{esc(title)}</title><style>{css}</style></head><body><a class="skip" href="#main">{esc(LABELS[lang]["read"])}</a><div class="page"><aside class="cover"><div class="cover-in">{cover}</div></aside><main class="sheet" id="main">{body}</main></div><script>{SCRIPT}</script></body></html>'''


def render(data, text, lang, available=("ko", "en"), digest="", raw=False):
    t = LABELS[lang]
    target, gd, lp = obj(data.get("target")), obj(data.get("get_dependencies")), obj(data.get("lookup_package"))
    verdict = evaluate(data)
    grade = verdict["overall"]
    name, version = target.get("name", ""), target.get("version", "")
    date = str(data.get("generated_at", ""))[:10]
    language = (
        '<nav class="language" aria-label="Language">'
        + "".join(
            f'<a href="report.{code}.html" lang="{code}" {"aria-current=page" if code == lang else ""}>{label}</a>'
            for code, label in [("ko", "한국어"), ("en", "English")]
            if code in available
        )
        + "</nav>"
    )
    stamp = f"""<div class="seal-wrap"><div class="seal st-{TOKENS[grade]}" style="--seal:160px"><svg class="seal-ring" viewBox="0 0 160 160" aria-hidden="true"><circle cx="80" cy="80" r="76" fill="none" stroke="currentColor" stroke-width="3"/><circle cx="80" cy="80" r="69" fill="none" stroke="currentColor"/></svg><div class="seal-text"><span class="seal-k">{t["verdict"]}</span><span class="seal-v">{t[grade]}</span><span class="seal-d">{esc(date)}</span></div></div><p class="seal-cap">{t["current"]}</p></div>"""
    nav = (
        '<nav class="arows">'
        + "".join(
            f'<a href="#{"dependencies" if area in ("license", "deps") else "vulnerabilities" if area == "vulns" else "maintenance"}"><span class="area-label">{t[area]}</span><strong class="st-{TOKENS[value]}">{t[value]}</strong></a>'
            for area, value in verdict["areas"].items()
        )
        + "</nav>"
    )
    if verdict.get("additional_policy"):
        nav = (
            nav.removesuffix("</nav>")
            + f'<a href="#additional-policy"><span class="area-label">{t["additional_policy"]}</span><strong class="st-{TOKENS[grade]}">{t[grade]}</strong></a></nav>'
        )
    actions = f'<div class="actions"><button data-print>{t["print"]}</button><a href="review.{lang}.md" download>{t["markdown"]}</a><a href="data.json" download>{t["snapshot"]}</a></div>'
    cover = (
        f'<a class="brand" href="#main"><span class="wordmark">OSS GATE</span><span class="brand-sub">{t["title"]}</span></a>'
        + language
        + stamp
        + f'<details class="details grade-guide"><summary>{t["grades"]}</summary><p>{t["grade_help"]}</p></details>'
        + nav
        + f'<nav class="toc"><a href="#main">{t["decision"]}</a><a href="#appendix">{t["appendix"]}</a></nav>'
        + actions
    )
    body = f'<header class="doc-head"><p class="meta">{esc(target.get("system"))} / {esc(date)}</p><h1 class="pkg">{esc(name)}<span class="ver">{esc(version)}</span></h1><p class="desc">{t["title"]}</p></header>'
    if data.get("schema") == "oss-gate.review/1":
        body += f'<p class="notice">{t["historical"]}</p>'
    additional = verdict.get("additional_policy")
    policy_section = ""
    if additional:
        rules = obj(obj(data.get("policy_context")).get("config")).get("review", {})
        explanation = "".join(
            f"<li>{esc(t.get(f['code'], f['code']))}"
            + (f' <span class="meta">{esc(f["destination"])}</span>' if f.get("destination") else "")
            + "</li>"
            for f in additional["findings"]
        )
        body += f'<p class="notice">{esc(additional["name"])} · {t["base_verdict"]}: {t[additional["base_overall"]]} · {t["effective_verdict"]}: <strong>{t[additional["overall"]]}</strong> · <a href="#additional-policy">{t["policy"]}</a></p>'
        policy_section = section(
            "additional-policy",
            t["additional_policy"],
            f"<p>{esc(additional['name'])} · {esc(additional['version'])}</p>"
            f"<p>{t['base_verdict']}: <strong>{t[additional['base_overall']]}</strong> · "
            f"{t['effective_verdict']}: <strong>{t[additional['overall']]}</strong></p>"
            + (f"<ul>{explanation}</ul>" if explanation else f"<p>{t['additional_pass']}</p>")
            + (
                f'<p class="legend-note">{t["communication_source"]}</p>'
                if rules.get("require_communication_review") or rules.get("blocked_destinations")
                else ""
            )
            + f'<p class="meta">{esc(additional["evaluated_at"])} · SHA-256 {esc(additional["sha256"])}</p>',
        )
    counts = obj(gd.get("counts"))
    metrics = [
        (t["direct"], counts.get("direct")),
        (t["indirect"], counts.get("indirect")),
        (
            t["advisories"],
            verdict["advisory_count"] if not verdict["coverage_gaps"] else f"{verdict['advisory_count']}*",
        ),
        (t["coverage"], len(verdict["coverage_gaps"])),
    ]
    _, reading = reading_sections(text, lang)
    body += reading
    body += policy_section
    body += f'<h2 class="appendix-title" id="appendix">{t["appendix"]}</h2>'
    body += section(
        "summary",
        t["summary"],
        '<div class="ledger">'
        + "".join(
            f'<div class="fig"><div class="fig-val">{esc(value) if value is not None else "?"}</div><div class="fig-label">{label}</div></div>'
            for label, value in metrics
        )
        + "</div>"
        + (
            f'<p class="legend-note">* {t["limits"]}: {esc(", ".join(verdict["coverage_gaps"]))}</p>'
            if verdict["coverage_gaps"]
            else ""
        ),
    )
    nodes = [dict(obj(n)) for n in seq(gd.get("nodes"))]
    for node in nodes:
        if (
            node.get("relation") == "SELF"
            and node.get("name") == lp.get("name")
            and node.get("version") == lp.get("version")
        ):
            node["licenses"] = lp.get("licenses")
            node["vulns_queried"] = isinstance(lp.get("advisories"), list)
            node["vuln_count"] = len(seq(lp.get("advisories")))

    cards = (
        '<div class="node-grid">'
        + "".join(
            f'<div class="node {"warn" if n.get("vuln_count") or classify_license(n.get("licenses"))["tier"] != "allow" else "unknown" if n.get("vuln_count") is None else ""}"><strong>{esc(n.get("name"))}</strong><small>{esc(n.get("version"))}</small><small>{esc(", ".join(seq(n.get("licenses")))) or t["missing"]}</small></div>'
            for n in nodes
            if n.get("relation") in ("SELF", "DIRECT")
        )
        + "</div>"
    )
    rows = [
        [
            n.get("name"),
            n.get("version"),
            n.get("relation"),
            ", ".join(seq(n.get("licenses"))) or t["missing"],
            n.get("vuln_count") if n.get("vulns_queried") and n.get("vuln_count") is not None else t["missing"],
            " → ".join(seq(n.get("path"))),
        ]
        for n in nodes
    ]
    deps = (
        (f'<p class="notice coverage">{t["fallback"]}</p>' if gd.get("fallback_used") else "")
        + cards
        + f'<p class="legend-note">{t["graph_note"]}</p>'
        + table([t["package"], t["version"], t["relation"], t["license"], t["vulns"], t["path"]], rows)
    )
    body += section("dependencies", t["tree"], deps)
    groups = advisory_groups(data.get("advisories"))
    vulns = (
        table(
            ["ID", t["score"], t["details"]],
            [[g["id"], g["score"] if g["score"] is not None else t["missing"], g["title"]] for g in groups],
        )
        if groups
        else f"<p>{t['no_vulns'] if not verdict['coverage_gaps'] else t['missing']}</p>"
    )
    vulns += "".join(details(g["id"] + " · " + t["details"], g) for g in groups)
    body += section("vulnerabilities", t["vulns"], vulns)
    sc = obj(obj(data.get("get_project")).get("scorecard"))
    body += section(
        "maintenance",
        t["maintenance"],
        f'<p class="meta">Scorecard · {esc(sc.get("date"))} · {esc(sc.get("overall"))}/10</p>'
        + (
            table(
                ["Check", t["score"], t["details"]],
                [[obj(c).get("name"), obj(c).get("score"), obj(c).get("reason")] for c in seq(sc.get("checks"))],
            )
            if sc
            else f"<p>{t['missing']}</p>"
        ),
    )
    body += section(
        "evidence",
        t["evidence"],
        f'<p class="notice">{t["notice"]}</p>'
        + details(t["policy"], verdict)
        + f'<p class="meta">data.json · SHA-256 {esc(digest)}</p>'
        + (f'<a href="api-responses.json" download>{t["raw"]}</a>' if raw else ""),
    )
    return shell(f"{name} {version} | OSS Gate", lang, cover, body)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--language", choices=("ko", "en", "both"), default="ko")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--no-webfonts", action="store_true", help="Compatibility option; reports always work offline")
    parser.add_argument(
        "--document-kind",
        choices=("document", "supplemental"),
        default="document",
        help="Label standalone analysis without creating an automated verdict",
    )
    parser.add_argument("--document", action="store_true", help="Render a standalone Markdown summary or proposal")
    args = parser.parse_args(argv)
    if args.document_kind != "document" and not args.document:
        parser.error("--document-kind requires --document")
    languages = ("ko", "en") if args.language == "both" else (args.language,)
    if args.out and (args.out.suffix.lower() != ".html" or args.out.is_symlink()):
        parser.error("--out must be a regular .html destination; evidence files cannot be overwritten")
    if args.out and len(languages) != 1:
        parser.error("--out requires one language")
    if args.document:
        if not args.out or len(languages) != 1:
            parser.error("--document requires --out and one language")
        text = args.source.read_text(encoding="utf-8")
        content = render_document(text, args.language, args.document_kind)
        args.out.write_text(content, encoding="utf-8", newline="\n")
        return 0
    data_path = args.source / "data.json" if args.source.is_dir() else args.source
    folder = data_path.parent
    try:
        data = load_review(data_path)
    except (OSError, ValueError, TypeError) as exc:
        parser.error(f"cannot load review evidence: {exc}")
    available = [lang for lang in ("ko", "en") if (folder / f"review.{lang}.md").is_file()]
    for lang in languages:
        source = folder / f"review.{lang}.md"
        if not source.exists() and lang == "ko" and (folder / "review.md").exists():
            source = folder / "review.md"
        if not source.exists():
            parser.error(f"missing {source.name}; translate the narrative before rendering")
    for lang in languages:
        source = folder / f"review.{lang}.md"
        if not source.exists():
            source = folder / "review.md"
        out = args.out or folder / f"report.{lang}.html"
        if out.is_symlink():
            parser.error("refusing to overwrite a symlink")
        out.write_text(
            render(
                data,
                source.read_text(encoding="utf-8"),
                lang,
                available,
                sha256(data_path),
                (folder / "api-responses.json").exists(),
            ),
            encoding="utf-8",
            newline="\n",
        )
        print(out)
    return 0
