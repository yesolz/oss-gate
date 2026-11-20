"""Regression tests for false approval, preserved evidence and hostile report input."""

import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/oss-gate"))
sys.path.insert(0, str(ROOT / "plugins/oss-gate/mcp/depsdev"))
import legacy_server
import server
from collect import collect
from core.licenses import classify_license
from core.policy import advisory_groups, evaluate
from core.render import render, render_document, narrative_parts, safe_url, markdown, main
from core.snapshot import new_run, seal, verify, write_json


def clean():
    return {
        "schema": "oss-gate.review/2",
        "target": {"system": "npm", "name": "demo", "version": "1.0.0"},
        "lookup_package": {"system": "npm", "name": "demo", "version": "1.0.0", "licenses": ["MIT"], "advisories": []},
        "root_osv": {"ids": [], "queried": True, "incomplete": False},
        "get_dependencies": {
            "version": "1.0.0",
            "nodes": [{"name": "demo", "version": "1.0.0", "relation": "SELF"}],
            "counts": {"direct": 0, "indirect": 0},
        },
        "advisories": {},
        "get_project": {"scorecard": {"overall": 8, "checks": []}},
    }


class ApiRegression(unittest.TestCase):
    def test_unscored_advisory_zero_is_unknown_unless_vector_confirms_it(self):
        vector = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
        zero_vector = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N"
        v4_vector = "CVSS:4.0/AV:N/AC:L/AT:P/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N"
        cases = [
            (0, "", [], None, None),
            (0, "", [{"type": "CVSS_V4", "score": v4_vector}], None, None),
            (0, "", [{"type": "CVSS_V3", "score": vector}], 9.8, "computed_from_vector"),
            (0, zero_vector, [], 0, "deps.dev"),
            (0, "invalid", [], None, None),
            (11, "", [], None, None),
        ]
        for score, raw_vector, severity, expected, source in cases:
            with self.subTest(score=score, vector=raw_vector, severity=severity):
                with legacy_server.fake(
                    {
                        legacy_server.ADV("PYSEC-example"): {
                            "advisoryKey": {"id": "PYSEC-example"},
                            "cvss3Score": score,
                            "cvss3Vector": raw_vector,
                        },
                        legacy_server.OSVV("PYSEC-example"): {"id": "PYSEC-example", "severity": severity},
                    }
                ):
                    advisory = server._get_advisory("PYSEC-example")
                self.assertEqual(advisory["cvss3_score"], expected)
                self.assertEqual(advisory["cvss3_score_source"], source)
                self.assertEqual(advisory["severity_label"], server.severity_label(expected))
                data = clean()
                data["advisories"] = {"PYSEC-example": advisory}
                data["root_osv"]["ids"] = ["PYSEC-example"]
                verdict = evaluate(data)
                self.assertEqual(verdict["severity_unknown_count"], int(expected is None))
                if expected is None:
                    self.assertEqual(verdict["areas"]["vulns"], "conditional")

    def test_original_offline_suite(self):
        with contextlib.redirect_stdout(io.StringIO()):
            for name in vars(legacy_server):
                if name.startswith("test_"):
                    with self.subTest(group=name):
                        getattr(legacy_server, name)()

    def test_spdx_false_approval(self):
        for expr in [
            "BSD-Proprietary",
            "MIT-only",
            "GPL-Nonsense",
            "MIT WITH made-up-exception",
            "SSPL-1.0",
            "MIT OR )",
            "LicenseRef-internal",
        ]:
            with self.subTest(expr=expr):
                self.assertEqual(classify_license(expr)["tier"], "hold")
        self.assertEqual(classify_license("EUPL-1.2")["tier"], "hold")
        self.assertEqual(classify_license("MIT OR GPL-3.0-only")["tier"], "allow")
        self.assertEqual(classify_license("MIT AND GPL-3.0-only")["tier"], "hold")

    def test_ranges_never_queried_as_installed_versions(self):
        fixture = json.dumps({"dependencies": {"ranged": "^1.2.3", "maximum": "<=9.0.0", "pinned": "2.0.0"}})
        with legacy_server.fake({legacy_server.QB: legacy_server.qb_echo(())}) as fake:
            result = server._audit_manifest(fixture, "package.json")
        self.assertEqual([p["name"] for p in result["packages"]], ["pinned"])
        self.assertEqual(len(result["skipped"]), 2)
        self.assertEqual(len(fake.calls[0][2]["queries"]), 1)

    def test_osv_failure_and_pagination_are_incomplete(self):
        with legacy_server.fake({legacy_server.QB: (503, {})}):
            values, incomplete = server._osv_batch([("npm", "demo", "1")])
        self.assertEqual(values, [None])
        self.assertTrue(incomplete)
        with legacy_server.fake({legacy_server.QB: {"results": [{"next_page_token": "next", "vulns": []}]}}):
            _, incomplete = server._osv_batch([("npm", "demo", "1")])
        self.assertTrue(incomplete)

    def test_malformed_osv_records_are_not_zero_findings(self):
        for payload in [{"vulns": "bad"}, {"vulns": [{}]}, {"vulns": [None]}, {"error": "quota"}]:
            with self.subTest(payload=payload), legacy_server.fake({legacy_server.QB: {"results": [payload]}}):
                values, incomplete = server._osv_batch([("npm", "demo", "1")])
                self.assertEqual(values, [None])
                self.assertTrue(incomplete)

    def test_partial_npm_versions_and_malformed_manifests(self):
        for version in ["1", "1.2", "01.2.3", "1.2.3-a..b", "1.2.3-01"]:
            self.assertFalse(server._pkgjson_spec(version)[1], version)
        self.assertTrue(server._pkgjson_spec("1.2.3-rc.1+build.2")[1])
        for source in ["[]", '{"dependencies": "invalid"}']:
            with self.assertRaises(server.ApiError):
                server.parse_manifest(source, "package.json")
        self.assertFalse(server.parse_manifest("demo==1.0 unexpected", "requirements.txt")[0]["pinned"])

    def test_collector_preserves_full_api_responses_and_unique_runs(self):
        routes = {
            legacy_server.PKG("npm", "demo"): {"versions": []},
            legacy_server.VER("npm", "demo", "1.0.0"): {
                "versionKey": {"name": "demo", "version": "1.0.0"},
                "licenses": ["MIT"],
                "extra_raw_field": "preserve me",
            },
            legacy_server.DEPS("npm", "demo", "1.0.0"): {
                "nodes": [{"versionKey": {"name": "demo", "version": "1.0.0"}, "relation": "SELF"}]
            },
            legacy_server.QB: legacy_server.qb_echo(()),
        }
        with tempfile.TemporaryDirectory() as tmp, legacy_server.fake(routes):
            first = collect(server, "npm", "demo", "1.0.0", output_root=tmp)
            second = collect(server, "npm", "demo", "1.0.0", output_root=tmp)
            self.assertNotEqual(first["folder"], second["folder"])
            folder = Path(first["folder"])
            self.assertIn("preserve me", (folder / "api-responses.json").read_text(encoding="utf-8"))
            verify(folder)
            self.assertEqual(first["verdict"]["overall"], "allow")


class PolicyRegression(unittest.TestCase):
    def test_allow_requires_measured_scope(self):
        self.assertEqual(evaluate(clean())["overall"], "allow")
        for change in [
            {"fallback_used": True, "resolved_version": "0.9.0"},
            {"truncated": True},
            {"osv_incomplete": True},
            {"nodes": []},
            {"graph_error": "partial"},
        ]:
            data = clean()
            data["get_dependencies"].update(change)
            with self.subTest(change=change):
                self.assertEqual(evaluate(data)["overall"], "conditional")
        data = clean()
        data["lookup_package"] = {"error": "timeout"}
        self.assertNotEqual(evaluate(data)["overall"], "allow")

    def test_fixed_high_still_blocks_reviewed_version(self):
        data = clean()
        data["lookup_package"]["advisories"] = ["GHSA-x"]
        data["advisories"] = {"GHSA-x": {"cvss3_score": 9.8, "fixed_versions": ["demo@2.0.0"]}}
        self.assertEqual(evaluate(data)["overall"], "hold")

    def test_aliases_are_transitively_deduplicated(self):
        groups = advisory_groups(
            {"A": {"aliases": ["B"], "cvss3_score": 8}, "C": {"aliases": ["D"]}, "B": {"aliases": ["C"]}}
        )
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["aliases"], ["A", "B", "C", "D"])
        self.assertEqual(groups[0]["score"], 8)

    def test_unknown_severity_and_failed_checks(self):
        data = clean()
        data["lookup_package"]["advisories"] = ["CVE-unknown"]
        self.assertEqual(evaluate(data)["overall"], "conditional")
        data = clean()
        data["verification"] = {"status": "FAIL"}
        self.assertEqual(evaluate(data)["overall"], "hold")
        data = clean()
        data["get_project"]["scorecard"] = {"overall": -1}
        self.assertEqual(evaluate(data)["areas"]["maintenance"], "unknown")

    def test_input_is_not_mutated(self):
        data = clean()
        before = copy.deepcopy(data)
        evaluate(data)
        render(data, "# Example", "en")
        self.assertEqual(data, before)

    def test_invalid_ids_and_mismatched_graph_never_allow(self):
        data = clean()
        data["lookup_package"]["advisories"] = [{"id": "invalid"}]
        self.assertNotEqual(evaluate(data)["overall"], "allow")
        data = clean()
        data["get_dependencies"]["nodes"][0]["name"] = "wrong-package"
        self.assertIn("graph_root_unverified", evaluate(data)["coverage_gaps"])
        data = clean()
        data["get_dependencies"]["nodes"].append(
            {
                "name": "child",
                "version": "1",
                "relation": "DIRECT",
                "licenses": ["MIT"],
                "licenses_queried": True,
                "vulns_queried": True,
                "vuln_count": 2,
                "vuln_ids": [],
            }
        )
        self.assertNotEqual(evaluate(data)["overall"], "allow")


class ReportRegression(unittest.TestCase):
    def test_opening_summary_precedes_data_without_losing_context(self):
        for opening in [
            "**Verdict: hold**\n\nReader-friendly reason.",
            "> **Decision:** hold.\n>\n> Reader-friendly reason.\n>\n> **Next step:** update after review.",
        ]:
            with self.subTest(opening=opening):
                source = "# Demo\n\nSnapshot context.\n\n" + opening + "\n\n## Details\nUnique narrative detail."
                page = render(clean(), source, "en")
                self.assertEqual(page.count("Reader-friendly reason."), 1)
                self.assertEqual(page.count("Unique narrative detail."), 1)
                self.assertIn("Snapshot context.", page)
                self.assertLess(page.index("Reader-friendly reason."), page.index('id="summary"'))
                self.assertLess(page.index("Unique narrative detail."), page.index('id="dependencies"'))
                # Model-authored wording cannot replace the deterministic seal.
                self.assertIn('class="seal-v">Allow<', page)

    def test_summary_split_preserves_references_fences_and_safe_markdown(self):
        source = """# Demo

Collected today.

> See [official evidence][source].
>
> ```text
> ## This is not a section boundary
> ```

## Actual section

![remote](https://example.com/pixel)
<script>bad()</script>

[source]: https://example.com/advisory
"""
        title, brief, context, rest = narrative_parts(source)
        self.assertEqual(title, "Demo")
        self.assertIn('href="https://example.com/advisory"', brief)
        self.assertIn("## This is not a section boundary", brief)
        self.assertIn("Collected today.", context)
        self.assertIn("Actual section", rest)
        self.assertNotIn("<script>", rest)
        self.assertNotIn("<img", rest)
        for text in ["A plain summary.", "# Only a title", "## First section\nText.", ""]:
            narrative_parts(text)

    def test_supplemental_document_never_implies_automated_approval(self):
        for lang, label in [("ko", "자동 판정 없음"), ("en", "No automated verdict")]:
            page = render_document("# Runtime\n\n> **Decision:** Hold.\n\n## Evidence\nSource.", lang, "supplemental")
            self.assertIn(label, page)
            self.assertNotIn('class="seal ', page)
            self.assertEqual(page.count("<h1"), 1)
            self.assertIn("Source.", page)
        with tempfile.TemporaryDirectory() as tmp:
            source, out = Path(tmp) / "review.md", Path(tmp) / "report.html"
            source.write_text("# Runtime\n\nScoped analysis.", encoding="utf-8")
            main([str(source), "--document", "--document-kind", "supplemental", "--language", "en", "--out", str(out)])
            self.assertIn("Supplemental analysis", out.read_text(encoding="utf-8"))
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main([str(source), "--document-kind", "supplemental"])

    def test_untrusted_html_and_links(self):
        data = clean()
        data["target"]["name"] = "</title><script>alert(1)</script>"
        result = render(
            data,
            "<script>alert(2)</script>\n\n[x](javascript:alert(1))\n\n![tracking](https://example.com/pixel)",
            "en",
        )
        self.assertNotIn("<script>alert", result)
        self.assertNotIn('href="javascript:', result)
        self.assertNotIn("<img ", result)
        self.assertIn("Content-Security-Policy", result)
        for url in ["javascript:alert(1)", "https://a\n.evil", "//evil", "https://u:p@host", "https://["]:
            self.assertIsNone(safe_url(url))
        self.assertEqual(safe_url("https://osv.dev/vulnerability/A"), "https://osv.dev/vulnerability/A")

    def test_language_and_missing_translation(self):
        for lang in ["ko", "en"]:
            result = render(clean(), "# Report", lang)
            self.assertIn(f'<html lang="{lang}">', result)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            write_json(folder / "data.json", clean())
            (folder / "review.ko.md").write_text("# 한국어", encoding="utf-8", newline="\n")
            seal(folder, ["data.json"])
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main([str(folder), "--language", "en"])
            self.assertFalse((folder / "report.en.html").exists())

    def test_tables_code_and_no_raw_html(self):
        rendered = markdown('| A | B |\n|---|---|\n| 1 | 2 |\n\n```sh\necho "hello"\n```\n\n<iframe src="x"></iframe>')
        self.assertIn("<table>", rendered)
        self.assertIn("<pre>", rendered)
        self.assertNotIn("<iframe", rendered)

    def test_evidence_integrity_and_path_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = new_run(tmp, "../../outside", "1/2")
            self.assertTrue(folder.is_relative_to(Path(tmp).resolve()))
            write_json(folder / "data.json", clean())
            seal(folder, ["data.json"])
            verify(folder)
            (folder / "data.json").write_text("{}", encoding="utf-8", newline="\n")
            with self.assertRaises(ValueError):
                verify(folder)
            (folder / "evidence-sha256.json").write_text(
                '{"../outside":"abc", "data.json":"abc"}', encoding="utf-8", newline="\n"
            )
            with self.assertRaises(ValueError):
                verify(folder)

    def test_renderer_refuses_overwriting_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            write_json(folder / "data.json", clean())
            seal(folder, ["data.json"])
            (folder / "review.en.md").write_text("# Review", encoding="utf-8", newline="\n")
            before = (folder / "data.json").read_bytes()
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main([str(folder), "--language", "en", "--out", str(folder / "data.json")])
            self.assertEqual(before, (folder / "data.json").read_bytes())

    def test_failed_sidecar_blocks_rendered_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            write_json(folder / "data.json", clean())
            seal(folder, ["data.json"])
            write_json(folder / "verification.json", {"status": "FAIL"})
            (folder / "review.en.md").write_text("# Review", encoding="utf-8", newline="\n")
            with contextlib.redirect_stdout(io.StringIO()):
                main([str(folder), "--language", "en"])
            self.assertIn(">Hold<", (folder / "report.en.html").read_text(encoding="utf-8"))

    def test_portfolio_missing_and_versions_remain_distinct(self):
        from core.portfolio import aggregate, compare

        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for index, version in enumerate(["1.0.0", "2.0.0"]):
                folder = Path(tmp) / str(index)
                folder.mkdir()
                data = clean()
                data["generated_at"] = "2026-11-17T00:00:00Z"
                data["target"]["version"] = version
                write_json(folder / "data.json", data)
                seal(folder, ["data.json"])
                paths.append(folder)
            current = aggregate(paths + [Path(tmp) / "missing"])
            self.assertEqual(current["review_count"], 2)
            self.assertEqual(len(current["excluded"]), 1)
            self.assertFalse(current["complete"])
            rows = compare(current, aggregate(paths[:1]))
            self.assertEqual(rows[1]["status"], "new_target")
            self.assertIsNone(rows[1]["previous"])

    def test_historical_snapshots_unchanged(self):
        from core.snapshot import sha256

        expected = json.loads((ROOT / "examples/snapshot-sha256.json").read_text(encoding="utf-8"))
        for path, digest in expected.items():
            self.assertEqual(sha256(ROOT / "examples" / path), digest)

    def test_portfolio_preserves_failed_verification_and_deduplicates(self):
        from core.portfolio import aggregate

        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for index, aid in enumerate(["GHSA-example", "CVE-example"]):
                folder = Path(tmp) / str(index)
                folder.mkdir()
                data = clean()
                data["generated_at"] = "2026-11-17T00:00:00Z"
                for key in ("target", "lookup_package"):
                    data[key]["name"] = f"package-{index}"
                data["get_dependencies"]["nodes"][0]["name"] = f"package-{index}"
                data["advisories"] = {aid: {"aliases": ["CVE-example"], "cvss3_score": 4.0}}
                data["lookup_package"]["advisories"] = [aid]
                write_json(folder / "data.json", data)
                seal(folder, ["data.json"])
                write_json(folder / "verification.json", {"status": "FAIL" if index == 0 else "WARN"})
                paths.append(folder)
            result = aggregate(paths)
            self.assertEqual(result["unique_advisory_groups"], 1)
            self.assertEqual(result["counts"], {"allow": 0, "conditional": 1, "hold": 1})

    def test_sealed_failure_cannot_be_cleared_by_sidecar(self):
        from core.snapshot import load_review

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            data = clean()
            data["verification"] = {"status": "FAIL"}
            write_json(folder / "data.json", data)
            seal(folder, ["data.json"])
            write_json(folder / "verification.json", {"status": "PASS"})
            self.assertEqual(evaluate(load_review(folder / "data.json"))["overall"], "hold")


if __name__ == "__main__":
    unittest.main()
