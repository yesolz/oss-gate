"""Build a read-only bilingual demo. No API, input form or model call is deployed."""

import html
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/oss-gate"))
from core.policy import evaluate
from core.render import LABELS

OUT = ROOT / "site/generated"
STYLE = """
:root{--paper:#f0f1ed;--white:#fff;--ink:#192229;--muted:#59646a;--rule:#ccd2cd;--blue:#213d7b;--yellow:#825e22;--red:#a44435;--sans:system-ui,-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;--serif:Georgia,"AppleMyungjo",serif;--mono:ui-monospace,SFMono-Regular,Consolas,monospace}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.7 var(--sans)}a{color:inherit;text-underline-offset:4px}header,main,footer{max-width:1180px;margin:auto;padding-left:32px;padding-right:32px}header{height:96px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--rule)}.wordmark{font-weight:800;letter-spacing:.08em;text-decoration:none;font-size:18px}.wordmark span{color:var(--blue)}nav{display:flex;gap:24px;font-size:12px;font-weight:600}nav a[aria-current]{color:var(--blue)}.hero{padding:76px 0 64px;display:grid;grid-template-columns:1.5fr 1fr;gap:70px;align-items:center}.eyebrow{font:11px var(--mono);letter-spacing:.1em;color:var(--blue);text-transform:uppercase}.hero h1{word-break:keep-all;font:500 clamp(42px,5vw,70px)/1.14 var(--serif);letter-spacing:-.045em;margin:24px 0}.hero p{font-size:16px;line-height:1.9;color:var(--muted);max-width:550px}.hero .actions{margin-top:30px;display:flex;gap:12px;flex-wrap:wrap}.button{font-size:13px;padding:12px 20px;border:1px solid var(--ink);text-decoration:none;background:var(--ink);color:white}.button.secondary{background:transparent;color:var(--ink)}.preview{background:var(--white);border:1px solid var(--rule);padding:32px;box-shadow:10px 10px 0 #e1e5df;transform:rotate(1deg)}.preview-top{display:flex;justify-content:space-between;border-bottom:1px solid var(--rule);padding-bottom:18px;font:10px var(--mono);color:var(--muted)}.preview h2{font:600 32px var(--serif);margin:26px 0 3px}.preview .version{font:13px var(--mono);color:var(--muted)}.stamp{width:110px;height:110px;border:3px double var(--yellow);border-radius:50%;color:var(--yellow);display:grid;align-content:center;text-align:center;float:right;font-weight:700;margin-top:22px;transform:rotate(-9deg)}.stamp small{font:9px var(--mono);letter-spacing:.05em}.preview dl{clear:both;padding-top:20px;font-size:12px}.preview dl div{display:flex;justify-content:space-between;border-top:1px solid var(--rule);padding:8px 0}.preview dt{color:var(--muted)}.preview dd{margin:0;font-weight:600}.preview p{font-size:11px;line-height:1.8;margin:20px 0 0}.section-head{display:flex;align-items:baseline;gap:18px;padding:28px 0;border-top:1px solid var(--ink);margin-top:36px}.section-head span{font:12px var(--mono);color:var(--blue)}.section-head h2{font:500 29px var(--serif);letter-spacing:-.02em;margin:0}.scope{display:grid;grid-template-columns:repeat(3,1fr);gap:36px;padding:0 0 40px}.scope h3{font-size:14px;margin:0 0 12px}.scope p{color:var(--muted);font-size:13px;margin:0}.note{border-left:2px solid var(--blue);padding:10px 18px;color:var(--muted);font-size:12px;margin:0 0 24px}.review-row{display:grid;grid-template-columns:52px 1.1fr 1.3fr 1fr;gap:24px;padding:24px 0;border-bottom:1px solid var(--rule);align-items:start}.review-row .num{font:12px var(--mono);color:var(--muted);padding-top:7px}.review-row h3{font-size:21px;line-height:1.3;margin:0 0 9px;letter-spacing:-.02em}.review-row .version{font:12px var(--mono);color:var(--muted)}.review-row p{font-size:13px;margin:0;color:var(--muted)}.review-row .links{display:flex;flex-wrap:wrap;gap:8px 14px;font-size:12px}.tag{font:600 11px var(--sans);color:var(--yellow);display:block;margin:0 0 14px}.tag.hold{color:var(--red)}.install{display:grid;grid-template-columns:1fr 1fr;gap:24px}.install article{padding:26px;background:var(--white);border:1px solid var(--rule)}.install h3{margin:0 0 15px;font-size:16px}.install pre{font:12px/2 var(--mono);overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere}.install p{font-size:12px;color:var(--muted)}.more{display:flex;gap:30px;flex-wrap:wrap;padding:24px 0;font-size:13px}.small{font-size:12px;color:var(--muted)}footer{margin-top:70px;padding-top:25px;padding-bottom:45px;border-top:1px solid var(--rule);display:flex;justify-content:space-between;gap:25px;color:var(--muted);font-size:11px}.skip{position:absolute;left:-9999px}.skip:focus{left:10px;top:10px;background:white;padding:10px;z-index:9}:focus-visible{outline:3px solid var(--blue);outline-offset:5px}
@media(max-width:800px){header,main,footer{padding-left:20px;padding-right:20px}header{height:76px}nav{gap:14px}.hero{grid-template-columns:1fr;padding-top:45px;gap:40px}.hero h1{font-size:48px}.preview{max-width:470px;width:100%;justify-self:center}.scope{grid-template-columns:1fr;gap:24px}.review-row{grid-template-columns:30px 1fr;gap:12px}.review-row p,.review-row .result{grid-column:2}.install{grid-template-columns:1fr}footer{display:block}footer p{margin-top:15px}}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto}}
"""
COPY = {
    "en": {
        "hero": "Know what you’re<br>bringing into your project.",
        "lead": "Turn a package or public repository into an adoption review. Understand the software, inspect the risks, and keep the evidence. All inside your own agent.",
        "browse": "Explore example reports",
        "install": "Install OSS Gate",
        "sub": "Your agent. Two MCPs. A review you can share.",
        "s1": "A decision with context",
        "a": "Understand the software",
        "ap": "Read what it does, how it handles data, and why its dependencies matter. Sources and uncertain claims stay visible.",
        "b": "See what needs attention",
        "bp": "License questions, known advisories, dependency paths and dated maintenance signals are brought together.",
        "c": "Keep the underlying evidence",
        "cp": "Markdown for collaboration, offline HTML for reading, and JSON snapshots with integrity hashes.",
        "s2": "Open the review files",
        "note": "Saved examples, collected November 17 and 22, 2026. Evaluated under policy v3. These are saved snapshots, not live scan results.",
        "r0": "An allow result with preserved API evidence and a matching dependency graph.",
        "r1": "A conditional decision caused by a dependency’s MPL-2.0 license.",
        "r2": "A previous-version graph leaves the requested version’s dependencies unverified.",
        "r3": "Known high-severity findings, dependency paths and license-review actions.",
        "r4": "No returned advisories in the snapshot; license questions still need review.",
        "open": "Read report",
        "md": "Markdown",
        "json": "Evidence JSON",
        "s3": "Use the agent you already have",
        "req": "Requires uv, Python 3.10+ and a local client with plugin/MCP support. Uses your existing agent account; its plan and service limits apply.",
        "guide": "Installation guide",
        "periodic": "Periodic portfolio report",
        "proposal": "Adoption proposal",
        "footer": "MIT-licensed project code. Public evidence retains its source terms.",
        "limit": "A screening aid, not a legal opinion or security certification.",
        "preview": "ADOPTION REVIEW",
        "stamp": "CONDITIONAL",
        "stampSub": "POLICY V3",
        "date": "SAVED 2026-11-17",
        "lic": "License review",
        "known": "Known advisories",
        "dep": "Direct dependencies",
        "licValue": "certifi · MPL-2.0",
        "prevNote": "A concrete question before adoption: review how certifi is modified and distributed.",
        "skip": "Skip to content",
    },
    "ko": {
        "hero": "오픈소스 도입,<br>이해하고 결정하세요.",
        "lead": "패키지나 공개 저장소를 이해하기 쉬운 도입 검토서로 정리합니다. 기능과 위험을 읽고, 판단의 근거까지 보관하세요. 내 에이전트 안에서 시작합니다.",
        "browse": "검토서 예제 읽기",
        "install": "OSS Gate 설치하기",
        "sub": "내 에이전트와 두 MCP로 만드는 도입 검토서.",
        "s1": "맥락이 있는 판단",
        "a": "소프트웨어 이해하기",
        "ap": "무엇을 하고, 데이터를 어떻게 처리하며, 왜 이 의존성을 쓰는지 읽습니다. 출처와 확인하지 못한 주장도 남깁니다.",
        "b": "확인할 항목 찾기",
        "bp": "라이선스 질문, 알려진 취약점, 의존성 경로와 기준일이 있는 유지보수 신호를 함께 살펴봅니다.",
        "c": "판단의 근거 보관하기",
        "cp": "협업에는 마크다운, 읽기에는 오프라인 HTML, 근거 확인에는 JSON 스냅샷과 무결성 해시를 사용합니다.",
        "s2": "검토서 파일 열어보기",
        "note": "2026년 11월 17일과 22일 수집한 자료를 정책 v3로 평가한 예제입니다. 저장된 스냅샷이며 실시간 검사 결과가 아닙니다.",
        "r0": "일치하는 의존성 그래프와 API 원문을 보존한 가능 판정 예제입니다.",
        "r1": "의존성의 MPL-2.0 라이선스로 조건부가 된 검토서입니다.",
        "r2": "이전 버전의 그래프로는 요청 버전의 의존성을 확인할 수 없습니다.",
        "r3": "높은 심각도 취약점과 의존성 경로, 라이선스 조치를 함께 봅니다.",
        "r4": "스냅샷의 알려진 권고는 0건이지만 라이선스 확인은 남아 있습니다.",
        "open": "검토서 읽기",
        "md": "마크다운",
        "json": "근거 JSON",
        "s3": "이미 쓰는 에이전트에서 시작하기",
        "req": "uv, Python 3.10 이상, 플러그인·MCP를 지원하는 로컬 클라이언트가 필요합니다. 기존 에이전트 계정을 사용하며 요금제와 서비스 한도는 적용됩니다.",
        "guide": "설치 안내",
        "periodic": "정기 현황 리포트",
        "proposal": "도입 제안서",
        "footer": "프로젝트 코드는 MIT 라이선스입니다. 외부 근거 자료의 이용 조건은 각각 유지됩니다.",
        "limit": "도입 검토를 돕는 자료이며 법적 판단이나 보안 인증이 아닙니다.",
        "preview": "오픈소스 도입 검토서",
        "stamp": "조건부",
        "stampSub": "POLICY V3",
        "date": "2026-11-17 자료",
        "lic": "라이선스 검토",
        "known": "알려진 권고",
        "dep": "직접 의존성",
        "licValue": "certifi · MPL-2.0",
        "prevNote": "도입 전 확인할 구체적인 질문: certifi를 어떻게 수정하고 배포하는가.",
        "skip": "본문으로 이동",
    },
}


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ["reviews", "periodic", "proposals"]:
        shutil.copytree(ROOT / "examples" / name, OUT / "examples" / name, dirs_exist_ok=True)
    for name in ["NOTICE.md", "snapshot-sha256.json"]:
        shutil.copyfile(ROOT / "examples" / name, OUT / "examples" / name)
    shutil.copyfile(ROOT / "NOTICE.md", OUT / "NOTICE.md")
    (OUT / "style.css").write_text(STYLE, encoding="utf-8", newline="\n")
    for lang in ["en", "ko"]:
        c = COPY[lang]
        ko = lang == "ko"
        specs = [
            ("pypi-packaging-26.3", "packaging", "r0"),
            ("psf-requests-2.34.2", "Requests", "r1"),
            ("fastapi-fastapi-0.163.1", "FastAPI", "r2"),
            ("npm-next-15.1.0", "Next.js", "r3"),
            ("npm-next-16.4.6", "Next.js", "r4"),
        ]
        rows = []
        for idx, (slug, name, desc) in enumerate(specs, 1):
            data = json.loads((ROOT / "examples/reviews" / slug / "data.json").read_text(encoding="utf-8"))
            grade = evaluate(data)["overall"]
            prefix = f"examples/reviews/{slug}"
            rows.append(
                f'<article class="review-row"><span class="num">0{idx}</span><div><h3>{name}</h3><span class="version">{html.escape(data["target"]["version"])}</span></div><p>{c[desc]}</p><div class="result"><span class="tag {grade}">{LABELS[lang][grade]}</span><div class="links"><a href="{prefix}/report.{lang}.html">{c["open"]} ↗</a><a href="{prefix}/review.{lang}.md" download>{c["md"]}</a><a href="{prefix}/data.json" download>{c["json"]}</a></div></div></article>'
            )
        guide = "https://github.com/yesolz/oss-gate/blob/main/docs/installation" + (".ko" if ko else "") + ".md"
        body = f'''<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'self'; base-uri 'none'; form-action 'none'"><meta name="description" content="{html.escape(c["sub"])}"><title>OSS Gate | {c["preview"]}</title><link rel="stylesheet" href="style.css"></head><body><a class="skip" href="#main">{c["skip"]}</a><header><a class="wordmark" href="index{".ko" if ko else ""}.html">OSS <span>GATE</span></a><nav aria-label="Language"><a href="index.ko.html" lang="ko" {'aria-current="page"' if ko else ""}>한국어</a><a href="index.html" lang="en" {'aria-current="page"' if not ko else ""}>English</a><a href="https://github.com/yesolz/oss-gate">GitHub ↗</a></nav></header><main id="main"><section class="hero"><div><div class="eyebrow">OSS Gate / v0.6.0</div><h1>{c["hero"]}</h1><p>{c["lead"]}</p><div class="actions"><a class="button" href="#reviews">{c["browse"]}</a><a class="button secondary" href="#install">{c["install"]}</a></div></div><aside class="preview" aria-label="{c["preview"]}"><div class="preview-top"><span>OSS GATE</span><span>{c["date"]}</span></div><div class="stamp"><small>{c["stampSub"]}</small>{c["stamp"]}</div><h2>requests</h2><span class="version">2.34.2 / PyPI</span><dl><div><dt>{c["lic"]}</dt><dd>{c["licValue"]}</dd></div><div><dt>{c["known"]}</dt><dd>0</dd></div><div><dt>{c["dep"]}</dt><dd>4</dd></div></dl><p>{c["prevNote"]}</p></aside></section><div class="section-head"><span>01</span><h2>{c["s1"]}</h2></div><section class="scope"><article><h3>{c["a"]}</h3><p>{c["ap"]}</p></article><article><h3>{c["b"]}</h3><p>{c["bp"]}</p></article><article><h3>{c["c"]}</h3><p>{c["cp"]}</p></article></section><section id="reviews"><div class="section-head"><span>02</span><h2>{c["s2"]}</h2></div><p class="note">{c["note"]}</p>{"".join(rows)}<div class="more"><a href="examples/periodic/2026-11-python-web.{lang}.html">{c["periodic"]} ↗</a><a href="examples/proposals/requests-adoption-2026-11.{lang}.html">{c["proposal"]} ↗</a></div></section><section id="install"><div class="section-head"><span>03</span><h2>{c["s3"]}</h2></div><div class="install"><article><h3>Claude Code</h3><pre>claude plugin marketplace add yesolz/oss-gate\nclaude plugin install oss-gate@oss-gate</pre></article><article><h3>Codex</h3><pre>codex plugin marketplace add yesolz/oss-gate\ncodex plugin add oss-gate@oss-gate</pre></article></div><p class="small">{c["req"]}</p><a href="{guide}">{c["guide"]} ↗</a></section></main><footer><span>© 2026 yesolz · <a href="NOTICE.md">{c["footer"]}</a></span><p>{c["limit"]}</p></footer></body></html>'''
        (OUT / ("index.ko.html" if ko else "index.html")).write_text(body, encoding="utf-8", newline="\n")
    (OUT / ".nojekyll").touch()
    print(OUT)


if __name__ == "__main__":
    build()
