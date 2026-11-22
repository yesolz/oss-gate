"""False-approval, decision provenance and policy/3 regressions."""

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/oss-gate"))
from core.licenses import classify_license, REVIEWED, IDS
from core.policy import evaluate
from core.reassess import reassess
from core.render import render
from core.settings import validate
from core.snapshot import seal, verify, write_json, load_review
from test_review import clean
from test_extensions import settings, with_policy


def conditional():
    data = clean()
    data["lookup_package"]["licenses"] = ["MPL-2.0"]
    return data


def decision(data):
    return {
        "finding_sha256": evaluate(data)["license_reviews"][0]["finding_sha256"],
        "decided_by": "Example reviewer",
        "decided_at": "2026-11-19T00:00:00Z",
        "reason": "Reviewed the intended use",
        "conditions": "Retain notices; recheck before distribution",
    }


class LicensePolicy(unittest.TestCase):
    def test_reviewed_missing_licenses_and_distinct_obligations(self):
        for item in (
            "Unicode-3.0 AND (Apache-2.0 OR MIT)",
            "Unicode-DFS-2016",
            "MIT-CMU",
            "HPND",
            "CDLA-Permissive-2.0",
            "BSD-3-Clause-Clear",
        ):
            with self.subTest(item=item):
                self.assertEqual(classify_license(item)["tier"], "allow")
        self.assertEqual(classify_license("CC-BY-4.0")["category"], "attribution")
        self.assertEqual(classify_license("CC-BY-4.0")["tier"], "conditional")
        self.assertIn("patent", REVIEWED["BSD-3-Clause-Clear"]["note"])
        self.assertTrue(set(REVIEWED) <= set(IDS.values()))

    def test_uncertainty_has_actionable_reasons_without_false_approval(self):
        for value, reason in [
            (None, "missing_metadata"),
            ("NOASSERTION", "missing_metadata"),
            ("SSPL-1.0", "unclassified_spdx"),
            ("LicenseRef-test", "custom_license"),
            ("MIT-made-up", "unrecognized_identifier"),
            ([123], "invalid_metadata"),
            ("GPL-3.0-only WITH Classpath-exception-2.0", "unsupported_exception"),
            ("MIT WITH Nope", "unrecognized_exception"),
            ("MIT OR", "invalid_expression"),
        ]:
            with self.subTest(value=value):
                result = classify_license(value)
                self.assertEqual(result["tier"], "hold")
                self.assertIn(reason, result["reasons"])

    def test_expression_precedence_choices_and_full_syntax_validation(self):
        value = classify_license("MIT OR (GPL-3.0-only AND NOASSERTION)")
        self.assertEqual(value["tier"], "allow")
        self.assertEqual(value["selected"], ["MIT"])
        self.assertEqual(value["choices"], ["MIT"])
        self.assertNotIn("missing_metadata", value["reasons"])
        self.assertEqual(classify_license("MIT AND (GPL-3.0-only OR Apache-2.0)")["tier"], "allow")
        for expr in [
            "MIT OR (",
            "MIT OR invalid!",
            "MIT WITH OR",
            "(MIT) WITH LLVM-exception",
            "MIT OR Apache-2.0 WITH )",
            "(" * 300 + "MIT" + ")" * 300,
        ]:
            self.assertEqual(classify_license(expr)["tier"], "hold", expr)
        self.assertEqual(classify_license("Apache-2.0 WITH LLVM-exception")["tier"], "allow")
        self.assertEqual(classify_license(["MIT", "GPL-3.0-only"])["tier"], "hold")

    def test_restrictions_preserve_or_alternatives_and_do_not_relax(self):
        self.assertEqual(classify_license("MIT OR Apache-2.0", {"MIT": "hold"})["selected"], ["Apache-2.0"])
        data = with_policy(clean(), settings(license_restrictions={"MIT": "hold"}))
        result = evaluate(data)
        self.assertEqual(result["overall"], "hold")
        self.assertEqual(result["areas"]["license"], "hold")
        self.assertEqual(result["additional_policy"]["base_overall"], "allow")
        self.assertEqual(result["additional_policy"]["overall"], "hold")
        self.assertEqual(result["additional_policy"]["findings"][0]["code"], "selected_license_restriction")
        self.assertNotIn("No additional blocking condition", render(data, "Review", "en"))
        data["lookup_package"]["licenses"] = ["GPL-3.0-only"]
        data = with_policy(data, settings(license_restrictions={"GPL-3.0-only": "conditional"}))
        self.assertEqual(evaluate(data)["overall"], "hold")

    def test_dependency_restrictions_are_not_limited_to_existing_warnings(self):
        data = clean()
        data["get_dependencies"]["nodes"].append(
            {
                "name": "child",
                "version": "1",
                "relation": "DIRECT",
                "licenses": ["MIT"],
                "licenses_queried": True,
                "vulns_queried": True,
                "vuln_count": 0,
                "vuln_ids": [],
            }
        )
        result = evaluate(with_policy(data, settings(license_restrictions={"MIT": "hold"})))
        self.assertEqual(len(result["license_reviews"]), 2)
        self.assertEqual(result["license_reviews"][1]["assessment"]["tier"], "hold")

    def test_acceptance_does_not_change_verdict_or_clear_unrelated_findings(self):
        data = conditional()
        entry = decision(data)
        reviewed = with_policy(data, settings(license_decisions=[entry]))
        result = evaluate(reviewed)
        self.assertEqual(result["overall"], "conditional")
        self.assertEqual(result["license_decisions"]["recorded"], 1)
        self.assertEqual(result["license_decisions"]["pending"], 0)
        reviewed["verification"] = {"status": "FAIL"}
        self.assertEqual(evaluate(reviewed)["overall"], "hold")
        reviewed["get_project"]["scorecard"]["overall"] = 1
        self.assertEqual(evaluate(reviewed)["areas"]["maintenance"], "hold")

    def test_changed_evidence_restrictions_or_target_invalidate_acceptance(self):
        data = conditional()
        entry = decision(data)
        for mutate in [
            lambda d: d["target"].update(version="2"),
            lambda d: d["lookup_package"].update(licenses=["MIT AND MPL-2.0"]),
            lambda d: d["get_dependencies"].update(truncated=True),
        ]:
            revised = copy.deepcopy(data)
            mutate(revised)
            value = evaluate(with_policy(revised, settings(license_decisions=[entry])))
            self.assertEqual(value["license_decisions"]["recorded"], 0)
        value = evaluate(
            with_policy(data, settings(license_decisions=[entry], license_restrictions={"MPL-2.0": "hold"}))
        )
        self.assertEqual(value["license_decisions"]["recorded"], 0)

    def test_expiry_future_and_unknown_decisions_are_not_counted(self):
        for changes, expected in [
            ({"expires_at": "2026-11-20T00:00:00Z"}, "expired"),
            ({"decided_at": "2026-11-21T00:00:00Z"}, "future_decision"),
        ]:
            data = conditional()
            entry = {**decision(data), **changes}
            value = evaluate(with_policy(data, settings(license_decisions=[entry])))
            self.assertEqual(value["license_decisions"]["items"][0]["status"], expected)
        data = clean()
        data["lookup_package"]["licenses"] = []
        value = evaluate(with_policy(data, settings(license_decisions=[decision(data)])))
        self.assertEqual(value["license_decisions"]["items"][0]["status"], "evidence_unresolved")

    def test_settings_reject_invalid_overrides_and_duplicate_records(self):
        for restriction in [{"*": "allow"}, {"MIT": "allow"}, {"unknown": "hold"}, {"MIT": False}]:
            with self.assertRaises(ValueError):
                validate(settings(license_restrictions=restriction))
        entry = decision(conditional())
        for entries in [
            [entry, entry],
            [{**entry, "decided_at": "2026-11-19"}],
            [{**entry, "reason": ""}],
            [{**entry, "expires_at": "2020-01-01T00:00:00Z"}],
        ]:
            with self.assertRaises(ValueError):
                validate(settings(license_decisions=entries))

    def test_bilingual_render_and_hostile_decisions(self):
        data = conditional()
        entry = {**decision(data), "reason": '<script>alert("test")</script>'}
        data = with_policy(data, settings(license_decisions=[entry]))
        for lang in ("ko", "en"):
            text = render(data, "Review", lang)
            self.assertIn('id="license-decisions"', text)
            self.assertNotIn(entry["reason"], text)
            self.assertIn('id="license-review"', text)
        data["verdict"] = {"policy": "oss-gate.policy/2"}
        self.assertIn("oss-gate.policy/2 → oss-gate.policy/3", render(data, "Review", "en"))

    def test_offline_reassessment_preserves_source_and_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "original"
            source.mkdir()
            data = conditional()
            data["verification"] = {"status": "FAIL"}
            write_json(source / "data.json", data)
            seal(source, ["data.json"])
            before = (source / "data.json").read_bytes()
            policy = root / "policy.json"
            write_json(policy, settings(license_decisions=[decision(data)]))
            result = reassess(source, root / "new", str(policy))
            folder = Path(result["folder"])
            verify(folder)
            self.assertFalse(result["network_performed"])
            self.assertEqual(load_review(folder / "data.json")["verdict"]["overall"], "hold")
            self.assertEqual((folder / "source-data.json").read_bytes(), before)
            self.assertEqual((source / "data.json").read_bytes(), before)

    def test_equivalent_pypi_graph_version_renders_root_license(self):
        data = clean()
        data["target"].update(system="pypi", name="packaging", version="26.3")
        data["lookup_package"].update(system="pypi", name="packaging", version="26.3")
        data["get_dependencies"].update(
            version="26.3.0", nodes=[{"name": "packaging", "version": "26.3.0", "relation": "SELF"}]
        )
        text = render(data, "Review", "en")
        self.assertIn("<small>26.3.0</small><small>MIT</small>", text)
        self.assertNotIn('<div class="node warn">', text)

    def test_policy_comparison_rejects_changed_classification_data(self):
        from core.portfolio import compare

        with self.assertRaises(ValueError):
            compare(
                {"policy": "oss-gate.policy/3", "classification_sha256": "a"},
                {"policy": "oss-gate.policy/3", "classification_sha256": "b"},
            )
