"""Offline regression fixtures for public API parsing and error handling."""
from __future__ import annotations

import asyncio
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote

import httpx

HERE = Path(__file__).resolve().parents[1] / "plugins/oss-gate/mcp/depsdev"
sys.path.insert(0, str(HERE.parents[1]))

from core import api as server  # noqa: E402

DD, OSV = server.DEPSDEV_BASE, server.OSV_BASE
_passed = 0


def check(cond: bool, label: str) -> None:
    global _passed
    if not cond:
        raise AssertionError(label)
    _passed += 1
    print(f"  ok  {label}")


def q(x: str) -> str:
    return quote(x, safe="")


def PKG(s, n): return f"{DD}/systems/{s}/packages/{q(n)}"
def VER(s, n, v): return f"{PKG(s, n)}/versions/{q(v)}"
def DEPS(s, n, v): return f"{VER(s, n, v)}:dependencies"
def ADV(i): return f"{DD}/advisories/{q(i)}"
def OSVV(i): return f"{OSV}/vulns/{q(i)}"
QB = f"{OSV}/querybatch"
RAW = object()


class FakeResp:
    def __init__(self, status, body):
        self.status_code, self._body = status, body

    def json(self):
        if self._body is RAW:
            raise ValueError("not json")
        return self._body


class FakeClient:
    """Map URLs to responses; missing routes return HTTP 404."""

    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get(self, url):
        self.calls.append(("GET", url, None))
        return self._resp(url, None)

    def post(self, url, json=None):
        self.calls.append(("POST", url, json))
        return self._resp(url, json)

    def _resp(self, url, body):
        v = self.routes.get(url, (404, RAW))
        if callable(v) and not isinstance(v, Exception):
            v = v(body)
        if isinstance(v, Exception):
            raise v
        return FakeResp(*v) if isinstance(v, tuple) else FakeResp(200, v)


@contextmanager
def fake(routes):
    fc, real = FakeClient(routes), server._client
    server._client = fc
    try:
        yield fc
    finally:
        server._client = real


def run(fn, *a, **kw) -> dict:
    out = json.loads(server._run(fn, *a, **kw))
    assert isinstance(out, dict), "tool result must be a JSON object"
    return out


def qb_echo(ids_per_query=("V-1",)):
    return lambda body: {"results": [{"vulns": [{"id": i} for i in ids_per_query]} for _ in body["queries"]]}


# ====================================================================== (a) unit
def test_license():
    print("[unit] classify_license (6 categories)")
    cl = server.classify_license
    cat = lambda x: cl(x)["category"]
    check(cat("MIT OR GPL-3.0") == "permissive", "OR -> loosest")
    check(cat("MIT AND GPL-3.0") == "strong-copyleft", "AND -> strictest")
    check(cat(["MIT", "AGPL-3.0"]) == "network-copyleft", "list -> strictest (AGPL network)")
    check(cat("(GPL-2.0 AND MIT) OR Apache-2.0") == "permissive", "parentheses")
    check(cat("Apache-2.0 WITH LLVM-exception") == "permissive", "WITH exception stripped")
    check(cat("LGPL-2.1-or-later") == "weak-copyleft", "LGPL -or-later")
    check(cat("MPL-2.0") == "weak-copyleft" and cat("EPL-2.0") == "weak-copyleft", "MPL/EPL weak")
    check(cat("GPL-3.0-only") == "strong-copyleft" and cat("GPL-2.0+") == "strong-copyleft", "GPL strong")
    check(cat("SSPL-1.0") == "unknown", "SSPL is not approved automatically")
    for u in ("non-standard", "", None, "LicenseRef-x", "Apache 2.0", ["LicenseRef-scancode-foo"]):
        check(cat(u) == "unknown", f"unknown: {u!r}")
    check("LicenseRef-x" in cl("LicenseRef-x")["reason"], "unrecognised id kept in reason")
    check(cl("MIT")["category"] == "permissive" and cl("MIT")["tier"] == "allow" and cl("MIT")["selected"] == ["MIT"], "string input and selected license")
    check(cl(["MIT", "LGPL-3.0"])["tier"] == "conditional", "weak -> conditional tier")
    check(cl(["GPL-2.0"])["tier"] == "hold" and cl([])["tier"] == "hold", "strong/unknown -> hold")
    check(cat("BSD-3-Clause") == "permissive" and cat("BlueOak-1.0.0") == "permissive" and cat("0BSD") == "permissive", "BSD family")
    check(cat("MIT OR") == "unknown" and cat("(MIT") == "unknown" and cat("MIT OR LicenseRef-y") == "permissive", "syntax errors unknown; OR with unknown loosest")
    check(cat([None, 3]) == "unknown", "non-str list items -> unknown, no exception")


def test_summarize():
    print("[unit] summarize_dep_licenses (synthetic graph)")
    nodes = [
        {"name": "root", "version": "1", "relation": "SELF", "licenses": None},
        {"name": "a", "version": "1", "relation": "DIRECT", "licenses": ["MIT"], "vuln_count": 1},
        {"name": "b", "version": "1", "relation": "INDIRECT", "licenses": ["GPL-3.0"], "vuln_count": 5},
        {"name": "c", "version": "1", "relation": "DIRECT", "licenses": ["MIT"], "vuln_count": 3},
        {"name": "d", "version": "1", "relation": "INDIRECT", "licenses": None, "license_error": "not found", "vuln_count": None},
        {"name": "e", "version": "1", "relation": "INDIRECT", "licenses": ["ISC"]},
    ]
    edges = [{"fromNode": 0, "toNode": 1}, {"fromNode": 1, "toNode": 2}, {"fromNode": 0, "toNode": 3},
             {"fromNode": 3, "toNode": 4}, {"fromNode": 9, "toNode": 1}, {"fromNode": "x"}]
    r = server.summarize_dep_licenses(nodes, edges)
    check(r["strictest_category"] == "unknown", "strictest == unknown (policy: unknown is strictest)")
    check(r["strictest_known_category"] == "strong-copyleft", "strictest_known == strong-copyleft (unknown excluded)")
    check(r["license_summary"] == {"permissive": 3, "attribution": 0, "weak-copyleft": 0, "strong-copyleft": 1, "network-copyleft": 0, "unknown": 1}, "summary counts")
    check(r["license_lookup_failures"] == 1, "lookup failures == 1")
    names = [x["name"] for x in r["non_permissive"]]
    check(names == ["d", "b"], "non_permissive strictest-first (unknown, then strong)")
    b = next(x for x in r["non_permissive"] if x["name"] == "b")
    check(b["path"] == ["root@1", "a@1", "b@1"] and b["license_category"] == "strong-copyleft", "b path via BFS")
    d = next(x for x in r["non_permissive"] if x["name"] == "d")
    check(d["license_category"] == "unknown" and d["licenses"] is None, "d unknown on lookup failure")
    check(r["nodes"][0]["path"] == ["root@1"] and r["nodes"][0]["license_category"] is None, "SELF path, not categorised")
    check(r["nodes"][5]["path"] is None, "unreachable node path null")
    check(r["edges_named"] == [["root@1", "a@1"], ["a@1", "b@1"], ["root@1", "c@1"], ["c@1", "d@1"]], "edges_named from valid edges only")
    check([(v["name"], v["vuln_count"]) for v in r["vulnerable_nodes"]] == [("c", 3), ("a", 1), ("b", 5)], "vulnerable_nodes: DIRECT first, then count desc")
    check(r["vulnerable_nodes"][2]["path"] == ["root@1", "a@1", "b@1"] and set(r["vulnerable_nodes"][0]) == {"name", "version", "relation", "vuln_count", "path"}, "vulnerable_nodes shape + path")
    check(server.summarize_dep_licenses([], [])["strictest_category"] is None, "empty graph")
    only_unknown = server.summarize_dep_licenses([nodes[0], {**nodes[4]}], [{"fromNode": 0, "toNode": 1}])
    check(only_unknown["strictest_category"] == "unknown" and only_unknown["license_summary"]["unknown"] == 1, "only unknown deps -> strictest unknown")
    r2 = server.summarize_dep_licenses([nodes[0], {**nodes[1], "licenses_queried": False}], edges[:1])
    check(r2["license_summary"]["permissive"] == 0 and r2["nodes"][1]["license_category"] is None, "unqueried node excluded")


def test_advisory_offline():
    print("[unit] get_advisory ranges / alias / errors")
    django = {"id": "PYSEC-2021-9", "aliases": ["CVE-2021-3281"], "affected": [{"package": {"name": "django", "ecosystem": "PyPI"},
              "ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "2.2"}, {"fixed": "2.2.18"}, {"introduced": "3.0"},
                                                          {"fixed": "3.0.12"}, {"introduced": "3.1"}, {"fixed": "3.1.6"}]}]}]}
    with fake({OSVV("PYSEC-2021-9"): django}) as fc:
        d = run(server._get_advisory, "PYSEC-2021-9")
    check(d["fixed_versions"] == ["django@2.2.18", "django@3.0.12", "django@3.1.6"], "all fixed versions kept (#1)")
    rs = d["affected"][0]["ranges"]
    check([(r["introduced"], r["fixed"]) for r in rs] == [("2.2", "2.2.18"), ("3.0", "3.0.12"), ("3.1", "3.1.6")], "ranges paired in order")
    check(d["sources"] == ["osv.dev"] and d["note"] is None and d["aliases"] == ["CVE-2021-3281"], "osv-only sources; self id not in aliases")

    git_only = {"id": "CVE-1", "aliases": ["GHSA-A"], "affected": [{"ranges": [{"type": "GIT", "repo": "https://x/y",
                "events": [{"introduced": "0"}, {"fixed": "abc"}]}]}]}
    ghsa = {"id": "GHSA-A", "aliases": ["CVE-1"], "summary": "lodash", "affected": [{"package": {"name": "lodash", "ecosystem": "npm"},
            "ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "0"}, {"fixed": "4.17.21"}]}]}]}
    with fake({ADV("CVE-1"): {"advisoryKey": {"id": "CVE-1"}, "aliases": ["GHSA-A"], "cvss3Score": 7.2}, OSVV("CVE-1"): git_only, OSVV("GHSA-A"): ghsa}) as fc:
        d = run(server._get_advisory, "CVE-1")
    check(d["fixed_versions"] == ["lodash@4.17.21"] and d["note"] is None, "GIT-only -> alias followed (#3)")
    check(d["sources"] == ["deps.dev", "osv.dev", "osv.dev:GHSA-A"] and d["cvss3_score"] == 7.2, "sources include alias")
    check(sum(1 for c in fc.calls if c[1] == OSVV("GHSA-A")) == 1, "exactly one extra alias GET")
    check(d["affected"][0]["package"] is None and d["affected"][0]["ranges"][0]["type"] == "GIT", "GIT range summarised without package")

    with fake({OSVV("CVE-2"): {**git_only, "id": "CVE-2", "aliases": []}}):
        d = run(server._get_advisory, "CVE-2")
    check(d["fixed_versions"] is None and d["note"] == "no ecosystem ranges; only GIT ranges", "GIT-only no alias -> null + note")
    with fake({OSVV("CVE-3"): {"id": "CVE-3", "affected": [{"package": {"name": "p", "ecosystem": "npm"},
               "ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "0"}]}]}]}}):
        d = run(server._get_advisory, "CVE-3")
    check(d["fixed_versions"] == [] and d["note"] is None, "ecosystem range without fix -> [] (genuinely unfixed)")
    with fake({ADV("X-1"): httpx.ConnectError("boom"), OSVV("X-1"): {"id": "X-1", "summary": "s"}}):
        d = run(server._get_advisory, "X-1")
    check(d["sources"] == ["osv.dev"] and d["source_errors"] == ["ConnectError"] and d["title"] == "s", "one source network error (#19)")
    with fake({ADV("X-2"): httpx.ReadTimeout("t"), OSVV("X-2"): (500, {})}):
        d = run(server._get_advisory, "X-2")
    check(d["error"].startswith("upstream error") and d["status"] is None, "both sources fail -> error")
    with fake({}):
        d = run(server._get_advisory, "GHSA-none")
    check(d == {"error": "not found", "status": 404}, "both 404 -> not found")


def test_advisory_narrative():
    print("[unit] advisory narrative: canonical_id / severity / CVSS / details / references")
    ci = server.canonical_id
    check(ci(["PYSEC-2024-38", "CVE-2024-24762", "GHSA-2jv5-9r88-3w3p", "GHSA-qf9m-vfgh-m389"]) == "GHSA-2jv5-9r88-3w3p", "GHSA preferred, alphabetical tie")
    check(ci(["PYSEC-1", "CVE-2"]) == "CVE-2" and ci(["RUSTSEC-1", "OSV-x", "GO-1"]) == "GO-1" and ci(["zzz", "PYSEC-9"]) == "PYSEC-9", "CVE > PYSEC/GO/RUSTSEC/OSV > other")
    check(ci(["foo"]) == "foo" and ci([]) is None and ci({"CVE-1"}) == "CVE-1" and ci([None, 3, ""]) is None, "edge inputs")
    sl = server.severity_label
    check([sl(x) for x in (None, "7.5", True, 0, 0.0, 3.9, 4.0, 6.9, 7.0, 8.9, 9.0, 10)] ==
          [None, None, None, "none", "none", "Low", "Medium", "Medium", "High", "High", "Critical", "Critical"], "severity_label boundaries")
    cv = server.cvss3_base_score
    check(cv("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H") == 7.5, "CVSS vector -> 7.5")
    check(cv("CVSS:3.1/AV:N/AC:L/PR:H/UI:N/S:U/C:H/I:H/A:H") == 7.2, "CVSS vector -> 7.2")
    check(cv("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H") == 10.0 and cv("CVSS:3.0/AV:L/AC:H/PR:H/UI:R/S:U/C:L/I:N/A:N") == 1.8, "scope changed max 10; 3.0 low vector")
    check(cv("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N") == 0.0, "no impact -> 0.0")
    check(cv("CVSS:2.0/AV:N") is None and cv("CVSS:3.1/AV:N/AC:L") is None and cv(None) is None and cv("CVSS:3.1/AV:X/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H") is None, "bad vectors -> None")

    long_details = "line one\nline two " * 200  # 3,800 chars
    refs = [{"type": "WEB", "url": "https://w1"}, {"type": "FIX", "url": "https://f1"}, {"type": "ADVISORY", "url": "https://a1"},
            {"type": "REPORT", "url": "https://r1"}, {"type": "WEB", "url": "https://w2"}, {"type": "WEB", "url": "https://w1"},
            {"type": "PACKAGE", "url": "https://p1"}, {"type": "WEB", "url": "https://w3"}, {"url": 5}]
    rec = {"id": "GHSA-N", "summary": "Short summary", "details": long_details, "aliases": ["CVE-2020-1"], "references": refs,
           "severity": [{"type": "CVSS_V3", "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H"}],
           "affected": [{"package": {"name": "p", "ecosystem": "npm"}, "ranges": [
               {"type": "GIT", "repo": "x", "events": [{"introduced": "0"}, {"fixed": "sha"}]},
               {"type": "SEMVER", "events": [{"introduced": "0"}, {"fixed": "1.2.0"}, {"introduced": "2.0.0"}, {"fixed": "2.0.3"}]}]}]}
    with fake({OSVV("GHSA-N"): rec}):
        d = run(server._get_advisory, "GHSA-N")
    check(d["cvss3_score"] == 7.5 and d["cvss3_score_source"] == "computed_from_vector" and d["severity_label"] == "High", "score computed from OSV vector")
    check(d["canonical_id"] == "GHSA-N" and d["summary"] == "Short summary" and d["title"] == "Short summary", "canonical + summary/title fallback")
    check(len(d["details"]) == 1801 and d["details"].endswith("…") and "\n" in d["details"], "details truncated to 1800 + ellipsis, newlines kept")
    check([r["url"] for r in d["references"]] == ["https://a1", "https://f1", "https://r1", "https://w1", "https://w2", "https://p1"], "references: ADVISORY/FIX/REPORT first, deduped, max 6")
    check(d["affected_summary"] == [{"ecosystem": "npm", "package": "p", "introduced": "0", "fixed": "1.2.0"},
                                    {"ecosystem": "npm", "package": "p", "introduced": "2.0.0", "fixed": "2.0.3"}], "affected_summary flattens ecosystem ranges only")
    with fake({ADV("GHSA-N"): {"advisoryKey": {"id": "GHSA-N"}, "cvss3Score": 9.1, "title": "T"}, OSVV("GHSA-N"): {**rec, "severity": [], "details": "short"}}):
        d = run(server._get_advisory, "GHSA-N")
    check(d["cvss3_score"] == 9.1 and d["cvss3_score_source"] == "deps.dev" and d["severity_label"] == "Critical" and d["details"] == "short", "deps.dev score preferred")
    with fake({OSVV("X-9"): {"id": "X-9", "aliases": ["CVE-2021-1"]}}):
        d = run(server._get_advisory, "X-9")
    check(d["cvss3_score"] is None and d["cvss3_score_source"] is None and d["severity_label"] is None and d["details"] is None
          and d["references"] == [] and d["canonical_id"] == "CVE-2021-1", "no score -> nulls; canonical from aliases")
    git_only = {"id": "CVE-1", "aliases": ["GHSA-A"], "affected": [{"ranges": [{"type": "GIT", "events": [{"introduced": "0"}, {"fixed": "abc"}]}]}]}
    ghsa = {"id": "GHSA-A", "details": "alias details", "references": [{"type": "ADVISORY", "url": "https://ga"}],
            "affected": [{"package": {"name": "lodash", "ecosystem": "npm"}, "ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "0"}, {"fixed": "4.17.21"}]}]}]}
    with fake({OSVV("CVE-1"): git_only, OSVV("GHSA-A"): ghsa}):
        d = run(server._get_advisory, "CVE-1")
    check(d["details"] == "alias details" and d["references"] == [{"type": "ADVISORY", "url": "https://ga"}] and d["canonical_id"] == "GHSA-A", "alias record supplies details/references")


def test_version_timeline():
    print("[unit] recent_versions / previous_version / 404 hint")
    vt = server.version_timeline
    vs = [{"versionKey": {"version": "1.0"}, "publishedAt": "2024-01-01T00:00:00Z"},
          {"versionKey": {"version": "3.0"}, "publishedAt": "2026-03-01T00:00:00Z", "isDefault": True},
          {"versionKey": {"version": "bad"}, "publishedAt": "not-a-date"},
          {"versionKey": {"version": "2.0"}, "publishedAt": "2025-01-01T00:00:00Z"},
          {"versionKey": {"version": "3.1rc1"}, "publishedAt": "2026-04-01T00:00:00Z"},
          {"versionKey": {"version": "nodate"}}]
    r = vt(vs, "3.0")
    check([x["version"] for x in r["recent_versions"]] == ["3.1rc1", "3.0", "2.0", "1.0", "bad", "nodate"], "desc by publishedAt, unparseable last (stable)")
    check(r["recent_versions"][1] == {"version": "3.0", "published_at": "2026-03-01T00:00:00Z", "is_default": True} and r["recent_versions"][0]["is_default"] is False, "entry shape + is_default flag")
    check(r["previous_version"] == "2.0", "previous = newest strictly older")
    check(vt(vs, "3.1rc1")["previous_version"] == "3.0" and vt(vs, "1.0")["previous_version"] is None, "previous of newest; oldest -> null")
    check(vt(vs, "bad")["previous_version"] is None and vt(vs, "missing")["previous_version"] is None, "unparseable/unknown selected -> null")
    many = [{"versionKey": {"version": str(i)}, "publishedAt": f"2020-01-{i + 1:02d}T00:00:00Z"} for i in range(12)]
    r = vt(many, "11")
    check(len(r["recent_versions"]) == 8 and r["recent_versions"][0]["version"] == "11" and r["previous_version"] == "10", "limit 8")
    check(vt([], "x") == {"recent_versions": [], "previous_version": None} and vt([1, "s"], "x")["recent_versions"] == [], "empty / junk input")
    pkg = {"versions": vs}
    with fake({PKG("pypi", "p"): pkg, VER("pypi", "p", "3.0"): {"versionKey": {"name": "p", "version": "3.0"}}}):
        d = run(server._lookup_package, "pypi", "p", "")
    check(d["version"] == "3.0" and d["previous_version"] == "2.0" and len(d["recent_versions"]) == 6, "lookup_package carries timeline (no extra call)")
    with fake({}):
        d = run(server._get_dependencies, "pypi", "p", "9.9.9", True, True, 10)
    check(d == {"error": "not found", "status": 404, "hint": "deps.dev has no resolved graph for this version yet; try previous_version from lookup_package"}, "graph 404 -> hint")
    with fake({DEPS("pypi", "p", "1"): (500, {})}):
        check(run(server._get_dependencies, "pypi", "p", "1", True, True, 10) == {"error": "upstream http 500", "status": 500}, "non-404 error has no hint")


def test_fallback_to_previous():
    print("[unit] get_dependencies fallback_to_previous")
    vs = [{"versionKey": {"version": f"v{i}"}, "publishedAt": f"2026-01-{i:02d}T00:00:00Z"} for i in range(1, 6)]
    graph = deps_fixture(2, 1)
    graph["nodes"][0]["versionKey"]["version"] = "v2"
    routes = {PKG("pypi", "root"): {"versions": vs}, DEPS("pypi", "root", "v2"): graph, QB: qb_echo()}
    with fake(routes) as fc:
        d = run(server._get_dependencies, "pypi", "root", "v5", True, False, 10, True)
    check(d["resolved_version"] == "v2" and d["requested_version"] == "v5" and d["version"] == "v2", "resolved v2 (v5 requested)")
    check(d["fallback_used"] is True and d["fallback_attempts"] == 3 and d["fallback_tried"] == ["v4", "v3"], "attempts=3 older tried, tried=[v4,v3]")
    check(d["nodes"][0]["relation"] == "SELF" and d["nodes"][0]["version"] == "v2" and d["counts"]["total"] == 4, "SELF shows resolved version; graph is v2's")
    gets = [c[1] for c in fc.calls if c[0] == "GET"]
    check(gets == [DEPS("pypi", "root", "v5"), PKG("pypi", "root"), DEPS("pypi", "root", "v4"), DEPS("pypi", "root", "v3"), DEPS("pypi", "root", "v2")], "call order: graph, versions, older graphs newest-first")
    check(all(n["vulns_queried"] for n in d["nodes"][1:]), "vuln batch ran on resolved graph")
    many = [{"versionKey": {"version": f"v{i}"}, "publishedAt": f"2026-01-{i:02d}T00:00:00Z"} for i in range(1, 13)]
    with fake({PKG("pypi", "root"): {"versions": many}}) as fc:
        d = run(server._get_dependencies, "pypi", "root", "v12", True, True, 10, True)
    check(d["error"] == "not found" and d["status"] == 404 and d["hint"] == server.GRAPH_404_HINT, "all 404 -> usual error + hint")
    check(d["fallback_tried"] == [f"v{i}" for i in range(11, 3, -1)] and len(d["fallback_tried"]) == 8, "bounded to 8 older attempts, newest first")
    check(sum(1 for c in fc.calls if c[0] == "GET") == 10, "1 + 1 + 8 = 10 GETs total")
    with fake({}) as fc:
        d = run(server._get_dependencies, "pypi", "root", "v5", True, True, 10, False)
    check(d == {"error": "not found", "status": 404, "hint": server.GRAPH_404_HINT} and len(fc.calls) == 1, "fallback off -> today's behaviour, no fallback_tried, 1 GET")
    with fake({}):
        d = run(server._get_dependencies, "pypi", "root", "v5", True, True, 10, True)
    check(d.get("fallback_tried") == [] and d["error"] == "not found", "package itself 404 during fallback -> error with empty fallback_tried")
    with fake({PKG("pypi", "root"): {"versions": vs}, DEPS("pypi", "root", "v1"): (500, {})}):
        d = run(server._get_dependencies, "pypi", "root", "v2", True, True, 10, True)
    check(d == {"error": "upstream http 500", "status": 500}, "non-404 during walk propagates")
    with fake({PKG("pypi", "root"): {"versions": vs}}):
        d = run(server._get_dependencies, "pypi", "root", "v1", True, True, 10, True)
    check(d["fallback_tried"] == [] and d["error"] == "not found", "requested is oldest -> nothing to try")
    ok = dict(routes); ok[DEPS("pypi", "root", "v5")] = graph
    with fake(ok) as fc:
        d = run(server._get_dependencies, "pypi", "root", "v5", True, False, 10, True)
    check(d["fallback_used"] is False and d["fallback_attempts"] == 0 and d["fallback_tried"] == [] and d["requested_version"] == d["resolved_version"] == "v5"
          and sum(1 for c in fc.calls if c[0] == "GET") == 1, "no fallback needed -> flags off, no versions GET")


def deps_fixture(n_direct=3, n_indirect=3):
    nodes = [{"versionKey": {"system": "NPM", "name": "root", "version": "1.0.0"}, "relation": "SELF"}]
    nodes += [{"versionKey": {"system": "NPM", "name": f"d{i}", "version": "1.0.0"}, "relation": "DIRECT"} for i in range(n_direct)]
    nodes += [{"versionKey": {"system": "NPM", "name": f"i{i}", "version": "1.0.0"}, "relation": "INDIRECT", "errors": ["x"] if i == 0 else []}
              for i in range(n_indirect)]
    edges = [{"fromNode": 0, "toNode": i + 1} for i in range(n_direct)]
    edges += [{"fromNode": 1, "toNode": n_direct + 1 + i} for i in range(n_indirect)]
    return {"nodes": nodes, "edges": edges, "error": ""}


def test_dependencies_offline():
    print("[unit] get_dependencies caps / null semantics (#6, #5)")
    routes = {DEPS("npm", "root", "1.0.0"): deps_fixture(), QB: qb_echo(("V-1", "V-2"))}
    routes.update({VER("npm", n, "1.0.0"): {"versionKey": {"name": n, "version": "1.0.0"}, "licenses": lic}
                   for n, lic in [("d0", ["MIT"]), ("d1", ["GPL-3.0"]), ("d2", ["MIT"]), ("i0", ["MIT"]), ("i1", ["AGPL-3.0"])]})
    with fake(routes) as fc:
        d = run(server._get_dependencies, "npm", "root", "1.0.0", True, True, 1)
    queried = [n for n in d["nodes"] if n["vulns_queried"]]
    check(d["truncated"] is True and len(queried) == 1 and queried[0]["name"] == "d0", "max_nodes=1 -> one DIRECT queried")
    check(queried[0]["vuln_count"] == 2 and queried[0]["vuln_ids"] == ["V-1", "V-2"] and queried[0]["licenses"] == ["MIT"], "queried node filled")
    others = [n for n in d["nodes"] if not n["vulns_queried"]]
    check(all(n["vuln_count"] is None and n["vuln_ids"] is None and n["licenses"] is None and n["license_category"] is None for n in others),
          "unqueried nodes null, not 0")
    check(d["license_summary"] == {"permissive": 1, "attribution": 0, "weak-copyleft": 0, "strong-copyleft": 0, "network-copyleft": 0, "unknown": 0}, "summary only over queried")
    check(sum(1 for c in fc.calls if c[0] == "GET") == 2 and sum(1 for c in fc.calls if c[0] == "POST") == 1, "upstream calls bounded: 1 graph + 1 version + 1 batch")
    check(d["nodes_with_errors"] == ["i0"] and d["counts"] == {"total": 7, "direct": 3, "indirect": 3}, "counts + error nodes")
    check(all(n["path"] and n["path"][0] == "root@1.0.0" for n in d["nodes"]), "every node path starts at SELF")
    for bad in (0, -1, "5", True):
        check(run(server._get_dependencies, "npm", "root", "1.0.0", True, True, bad)["error"] == "invalid input: max_nodes must be between 1 and 2000", f"max_nodes={bad!r} rejected")

    with fake(routes) as fc:
        d = run(server._get_dependencies, "npm", "root", "1.0.0", True, True, 200)
    check(d["truncated"] is False and d["license_lookup_failures"] == 1 and d["nodes"][-1]["license_error"] == "not found", "i2 missing -> lookup failure recorded")
    check(d["strictest_category"] == "unknown" and d["strictest_known_category"] == "network-copyleft" and [x["name"] for x in d["non_permissive"]] == ["i2", "i1", "d1"], "strictest == unknown (policy), strictest_known == network; non_permissive order: unknown, network, strong")
    check(len({c[1] for c in fc.calls if c[0] == "GET"}) == 7, "licenses deduped by name+version (6 nodes + graph)")
    with fake(routes) as fc:
        d = run(server._get_dependencies, "npm", "root", "1.0.0", False, False, 200)
    check(d["license_summary"] is None and d["non_permissive"] is None and len(fc.calls) == 1, "include_* False -> no extra calls, summary null")
    check(all(n["vuln_count"] is None and n["vulns_queried"] is False for n in d["nodes"]), "include_vulns=False -> null")
    short = dict(routes)
    short[QB] = lambda body: {"results": [{"vulns": []}]}
    with fake(short):
        d = run(server._get_dependencies, "npm", "root", "1.0.0", True, False, 200)
    check(d["osv_incomplete"] is True and sum(1 for n in d["nodes"] if n["vulns_queried"]) == 1, "short OSV batch -> padded None + osv_incomplete (#24)")


def test_manifest_parsing():
    print("[unit] parse_manifest pinned table (#7, #17, #18, #25)")
    pj = json.dumps({"dependencies": {"a": "1.x", "b": "1.2.*", "c": "v1.2.3", "d": "1.0.0-", "e": "1.0.0-beta.1",
                                      "f": "npm:alias@1.0.0", "g": "npm:@scope/x@^2.0.0", "h": "^1.2.3", "i": "1.0.0+build.5"},
                     "peerDependencies": {"zz": "1.0.0"}})
    got = {e.get("aliased_from", e["name"]): e for e in server.parse_manifest(pj, "package.json")}
    check(got["a"]["version"] == "" and got["b"]["version"] == "", "1.x / 1.2.* are ranges")
    check(got["c"] == {"name": "c", "version": "v1.2.3", "pinned": True, "group": "dependencies"}, "v-prefixed kept as-is")
    check(got["d"]["version"] == "" and got["e"] == {"name": "e", "version": "1.0.0-beta.1", "pinned": True, "group": "dependencies"}, "dangling dash rejected; prerelease ok")
    check(got["f"] == {"name": "alias", "version": "1.0.0", "pinned": True, "aliased_from": "f", "group": "dependencies"}, "npm:alias@ver")
    check(got["g"]["name"] == "@scope/x" and got["g"]["version"] == "" and got["g"]["pinned"] is False, "npm:@scope/x@^ver")
    check(got["h"] == {"name": "h", "version": "", "pinned": False, "group": "dependencies"} and got["i"]["pinned"] is True, "caret skipped; build metadata")
    check(got["zz"]["group"] == "peerDependencies", "peerDependencies included")
    req = "a==1.0.*\nfoo===1.0\nbar==2.0\\\nbaz == 3.1 ; python_version>'3'\nqux>=1\n"
    got = {e["name"]: e for e in server.parse_manifest(req, "requirements.txt")}
    check(got["a"]["version"] == "" and got["foo"]["version"] == "", "==1.0.* and === are not pins")
    check(got["bar"]["version"] == "2.0" and got["baz"] == {"name": "baz", "version": "3.1", "pinned": True}, "backslash/marker stripped")
    check(got["qux"]["pinned"] is False and len(got) == 5, "unpinned recorded")
    gomod = ("module m\n\ngo 1.21\n\nrequire(\n\ta.com/x v1.0.0 // indirect\n\tb.com/y v1.1.0\n\tc.com/z v2.0.0\n)\n"
             "replace (\n\ta.com/x => a.com/xfork v1.0.1\n\tb.com/y v1.1.0 => ../local\n)\nreplace c.com/z v9.9.9 => c.com/zz v3.0.0\n"
             "require d.com/w v0.1.0\n")
    got = {e.get("replaced_from", e["name"] + "@" + e["version"]): e for e in server.parse_manifest(gomod, "go.mod")}
    x = got["a.com/x@v1.0.0"]
    check(x["name"] == "a.com/xfork" and x["version"] == "v1.0.1" and x["indirect"] is True, "replace applied + indirect flag; require( without space")
    check(got["b.com/y@v1.1.0"]["version"] == "" and got["b.com/y@v1.1.0"]["note"] == "replaced by local path", "local-path replace -> skipped")
    check(got["c.com/z@v2.0.0"]["name"] == "c.com/z" and "replaced_from" not in got["c.com/z@v2.0.0"], "replace with non-matching version ignored")
    check(got["d.com/w@v0.1.0"]["indirect"] is False, "single-line require")
    for bad in (("x", "Cargo.toml"), (123, "go.mod")):
        check("error" in run(server._audit_manifest, *bad), f"bad manifest input {bad[1]} -> error")


def test_validation_and_urls():
    print("[unit] input validation + URL capture (#9)")
    with fake({}) as fc:
        for nm in ("", ".", "..", "a/../b", "   "):
            check("invalid input" in run(server._lookup_package, "pypi", nm, "")["error"], f"name {nm!r} rejected")
        check("invalid input" in run(server._get_dependencies, "pypi", "x", "..", True, True, 5)["error"], "version '..' rejected")
        check("invalid input" in run(server._get_advisory, ".")["error"] and "invalid input" in run(server._get_advisory, "")["error"], "advisory id rejected")
        check(fc.calls == [], "no upstream call on rejected input")
    pkg = {"versions": [{"versionKey": {"version": "1.0.0"}, "publishedAt": "2024-01-01T00:00:00Z"},
                        {"versionKey": {"version": "2.0.0"}, "publishedAt": "2025-01-01T00:00:00Z", "isDefault": True}]}
    det = {"versionKey": {"name": "@anthropic-ai/claude-code", "version": "2.0.0"}, "licenses": ["non-standard"],
           "relatedProjects": [{"projectKey": {"id": "github.com/anthropics/claude-code"}}],
           "links": [{"label": "HOMEPAGE", "url": "https://github.com/Anthropics/claude-code"}]}
    with fake({PKG("npm", "@anthropic-ai/claude-code"): pkg, VER("npm", "@anthropic-ai/claude-code", "2.0.0"): det}) as fc:
        d = run(server._lookup_package, "NPM", "@anthropic-ai/claude-code", "")
    check(fc.calls[0][1] == f"{DD}/systems/npm/packages/%40anthropic-ai%2Fclaude-code", "scoped name encoded, system lowercased")
    check(all(c[1].startswith((DD, OSV)) for c in fc.calls), "only the two host constants")
    check(d["version"] == "2.0.0" and d["license_policy"]["category"] == "unknown" and d["repo_candidates"] == ["anthropics/claude-code"], "default version + policy + candidates")
    with fake({PKG("npm", "p"): pkg, VER("npm", "p", "2.0.0"): {"versionKey": {"version": "9.9.9"}}}):
        check(run(server._lookup_package, "npm", "p", "")["error"] == "version mismatch from upstream", "version mismatch detected")
    nodef = {"versions": [{"versionKey": {"version": "a"}, "publishedAt": "2020-01-01T00:00:00Z"},
                          {"versionKey": {"version": "b"}, "publishedAt": "2023-06-01T00:00:00Z"}, {"versionKey": {"version": "c"}}]}
    with fake({PKG("npm", "p"): nodef, VER("npm", "p", "b"): {"versionKey": {"name": "p", "version": "b"}}}):
        d = run(server._lookup_package, "npm", "p", "")
    check(d["version"] == "b" and d["latest_version"] == "b", "no isDefault -> newest publishedAt (#20)")
    with fake({PKG("npm", "p"): {"versions": [{"versionKey": {"version": "c"}}]}}):
        d = run(server._lookup_package, "npm", "p", "")
    check(d["error"].startswith("package has no resolvable") and d["status"] == 404, "no parseable dates -> error")
    with fake({PKG("npm", "p"): {"versions": [{"versionKey": {"version": "c"}}]}, VER("npm", "p", "c"): {"versionKey": {"name": "p", "version": "c"}}}):
        check(run(server._lookup_package, "npm", "p", "c")["latest_version"] is None, "explicit version, latest null")


def test_fuzz_shapes():
    print("[unit] upstream shape fuzz (#8)")
    for body in ([], "s", (200, None), {"versions": [1]}, {"versions": "x"}, (200, RAW), (503, {})):
        with fake({PKG("pypi", "p"): body, VER("pypi", "p", "1"): body}):
            d = run(server._lookup_package, "pypi", "p", "1")
        check("error" in d or isinstance(d, dict), f"lookup fuzz {body!r} -> JSON")
    with fake({PKG("pypi", "p"): {"versions": [{"versionKey": {"version": "1"}, "isDefault": True}]},
               VER("pypi", "p", "1"): {"versionKey": {"name": "p", "version": "1"}, "licenses": "MIT", "links": "x", "relatedProjects": [1], "advisoryKeys": [{"id": None}]}}):
        d = run(server._lookup_package, "pypi", "p", "")
    check(d["licenses"] == [] and d["license_policy"]["category"] == "unknown" and d["links"] == [] and d["advisories"] == [], "licenses:'MIT' str & junk fields tolerated")
    for body in ({"nodes": [1], "edges": "x"}, {"nodes": "x"}, [], {"nodes": [{"versionKey": 5, "relation": None}]}):
        with fake({DEPS("pypi", "p", "1"): body, QB: {"results": "abc"}}):
            d = run(server._get_dependencies, "pypi", "p", "1", True, True, 10)
        check(isinstance(d, dict) and ("error" in d or d["counts"]["total"] <= 1), f"deps fuzz {body!r}")
    fx = deps_fixture(1, 0)
    with fake({DEPS("pypi", "p", "1"): fx, QB: {"results": "abc"}, VER("pypi", "d0", "1.0.0"): "str"}):
        d = run(server._get_dependencies, "pypi", "p", "1", True, True, 10)
    check(d["osv_incomplete"] is True and d["nodes"][1]["vulns_queried"] is False and d["nodes"][1]["license_error"] == "unexpected upstream shape",
          "OSV results:'abc' -> incomplete; version body str -> license_error")
    for body in ([], "s", {"affected": "x"}, {"affected": [{"ranges": [{"events": "x"}]}]}, {"aliases": [5]}):
        with fake({OSVV("A-1"): body}):
            check(isinstance(run(server._get_advisory, "A-1"), dict), f"advisory fuzz {body!r}")
    for body in ([], {"scorecard": "x", "starsCount": "many"}, {"scorecard": {"checks": [1]}}):
        with fake({f"{DD}/projects/{q('github.com/o/r')}": body, f"{DD}/projects/{q('github.com/o/r')}:packageversions": {"versions": [1, {"versionKey": "x"}]}}):
            check(isinstance(run(server._get_project, "o/r"), dict), f"project fuzz {body!r}")
    with fake({QB: {"results": [[], 1]}}):
        d = run(server._audit_manifest, "a==1\nb==2\n", "requirements.txt")
    check(d["packages"][0]["vuln_count"] is None and d["packages"][0]["vulns_queried"] is False and d["summary"]["with_vulns"] == 0, "batch non-dict results -> null")


def test_caps():
    print("[unit] caps (#5)")
    big = "\n".join(f"pkg{i}==1.0.0" for i in range(3000))
    with fake({QB: qb_echo()}) as fc:
        d = run(server._audit_manifest, big, "requirements.txt")
    check(d["error"] == "invalid input: more than 2000 entries" and fc.calls == [], ">2000 entries rejected, 0 POSTs")
    with fake({QB: qb_echo()}) as fc:
        d = run(server._audit_manifest, "x" * 512_001, "requirements.txt")
    check(d["error"].startswith("invalid input: text exceeds") and fc.calls == [], ">512k chars rejected")
    with fake({QB: qb_echo()}) as fc:
        d = run(server._audit_manifest, "\n".join(f"pkg{i}==1.0.0" for i in range(1200)), "requirements.txt")
    check(d["summary"]["packages"] == 1200 and sum(1 for c in fc.calls if c[0] == "POST") == 3, "1200 entries -> 3 batches of <=500")


def test_project_helpers():
    print("[unit] primary_package + repo_candidates")
    pick = server.pick_primary_package
    pid = "github.com/anthropics/claude-code"
    pk = [{"system": "go", "name": "github.com/anthropics/claude-code", "versions": 489}, {"system": "go", "name": "github.com/AnthropicS/claude-code", "versions": 480},
          {"system": "npm", "name": "@anthropic-ai/claude-code", "versions": 84}, {"system": "npm", "name": "claude-code", "versions": 3},
          {"system": "pypi", "name": "anycode-ai", "versions": 500}]
    check(pick(pid, pk)["name"] == "@anthropic-ai/claude-code", "name match beats most versions; scoped match; tie by versions")
    check(pick("github.com/o/r", pk[4:] + [{"system": "npm", "name": "b", "versions": 900}])["name"] == "b", "no match -> most versions")
    check(pick(pid, pk[:2]) is None and pick(pid, []) is None, "only GO pseudo-packages -> null")
    check(pick("github.com/o/r", [{"system": "npm", "name": "x"}])["name"] == "x", "missing versions tolerated")
    det = {"relatedProjects": [{"projectKey": {"id": "github.com/a/b"}}, {"projectKey": {"id": "gitlab.com/g/h"}}, {"projectKey": 5}],
           "links": [{"url": "https://github.com/c/d/issues"}, {"url": "https://github.com/A/B"}, {"url": "https://x.dev"}, {"url": "https://github.com/"}, {"label": "X"}]}
    check(server._repo_candidates(det) == ["a/b", "c/d"], "repo_candidates: relatedProjects first, links next, deduped, non-github dropped")
    check(server._repo_candidates({}) == [], "no candidates")
    dup = {"relatedProjects": [{"projectKey": {"id": "github.com/fastapi/fastapi"}, "relationType": "SOURCE_REPO"},
                               {"projectKey": {"id": "github.com/FastAPI/fastapi"}, "relationType": "ISSUE_TRACKER"},
                               {"projectKey": {"id": "github.com/fastapi/fastapi"}}, {"projectKey": {"id": ""}}, {"projectKey": {"id": None}}],
           "links": [{"url": "https://github.com/FastAPI/FastAPI"}]}
    check(server._related_project_ids(dup) == ["github.com/fastapi/fastapi"], "related_projects deduped case-insensitively, first spelling kept")
    check(server._repo_candidates(dup) == ["fastapi/fastapi"], "repo_candidates deduped the same way")
    pkg1 = {"versions": [{"versionKey": {"version": "1"}, "isDefault": True}]}
    with fake({PKG("pypi", "fastapi"): pkg1, VER("pypi", "fastapi", "1"): {"versionKey": {"name": "fastapi", "version": "1"}, **dup}}) as fc:
        d = run(server._lookup_package, "pypi", "fastapi", "")
    check(d["related_projects"] == ["github.com/fastapi/fastapi"] and d["repo_candidates"] == ["fastapi/fastapi"] and len(fc.calls) == 3, "lookup output deduped; single project GET")
    print("[unit] project check reasons + lookup description")
    proj_url = f"{DD}/projects/{q('github.com/o/r')}"
    proj = {"projectKey": {"id": "github.com/o/r"}, "description": "Desc", "homepage": "https://o.example", "starsCount": 5,
            "scorecard": {"date": "2026-01-01", "overallScore": 6.5, "checks": [{"name": "Maintained", "score": 10, "reason": "r" * 300}, {"name": "X", "score": -1}]}}
    with fake({proj_url: proj}):
        d = run(server._get_project, "o/r")
    check(d["description"] == "Desc" and d["homepage"] == "https://o.example", "project description passthrough")
    ch = d["scorecard"]["checks"]
    check(ch[0]["reason"] == "r" * 200 + "…" and len(ch[0]["reason"]) == 201 and ch[1]["reason"] is None and set(ch[0]) == {"name", "score", "reason"}, "check reason truncated to 200")
    check(d["packages_error"] == "not found" and d["primary_package"] is None, "packageversions 404 tolerated")
    pkg = {"versions": [{"versionKey": {"version": "1.0.0"}, "isDefault": True}]}
    det = {"versionKey": {"name": "p", "version": "1.0.0"}, "licenses": ["MIT"], "relatedProjects": [{"projectKey": {"id": "github.com/o/r"}}]}
    with fake({PKG("pypi", "p"): pkg, VER("pypi", "p", "1.0.0"): det, proj_url: proj}) as fc:
        d = run(server._lookup_package, "pypi", "p", "")
    check(d["description"] == "Desc" and d["homepage"] == "https://o.example" and len(fc.calls) == 3, "lookup description via relatedProjects[0] (one extra GET)")
    with fake({PKG("pypi", "p"): pkg, VER("pypi", "p", "1.0.0"): {**det, "relatedProjects": []}}) as fc:
        d = run(server._lookup_package, "pypi", "p", "")
    check(d["description"] is None and d["homepage"] is None and len(fc.calls) == 2, "no related project -> no extra GET, null")
    with fake({PKG("pypi", "p"): pkg, VER("pypi", "p", "1.0.0"): det, proj_url: httpx.ConnectError("x")}):
        d = run(server._lookup_package, "pypi", "p", "")
    check(d["description"] is None and d["version"] == "1.0.0", "project fetch failure -> null, lookup still succeeds")
