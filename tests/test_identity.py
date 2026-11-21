"""Real PyPI normalization regressions and negative identity boundaries."""

import copy
import json
import unittest

import legacy_server as fixtures
from test_review import clean
from core import api
from core.identity import same_version
from core.policy import evaluate
from core.registry import check_registry


class PackageIdentity(unittest.TestCase):
    def test_seven_self_audit_failures_and_preserved_requested_version(self):
        pairs = [
            ("boolean-py", "5.0", "5.0.0"),
            ("idna", "3.20", "3.20.0"),
            ("packaging", "26.3", "26.3.0"),
            ("pip", "26.3", "26.3.0"),
            ("pycparser", "3.11", "3.11.0"),
            ("pycparser", "3.12", "3.12.0"),
            ("pywin32", "312", "312.0.0"),
        ]
        for name, requested, canonical in pairs:
            with (
                self.subTest(name=name, requested=requested),
                fixtures.fake(
                    {
                        fixtures.PKG("pypi", name): {
                            "versions": [
                                {"versionKey": {"version": "1.0"}, "publishedAt": "2020-01-01T00:00:00Z"},
                                {"versionKey": {"version": canonical}, "publishedAt": "2025-01-01T00:00:00Z"},
                            ]
                        },
                        fixtures.VER("pypi", name, requested): {
                            "versionKey": {"system": "PYPI", "name": name, "version": canonical},
                            "licenses": ["MIT"],
                        },
                    }
                ),
            ):
                result = api._lookup_package("pypi", name, requested)
                self.assertEqual(result["version"], requested)
                self.assertEqual(result["previous_version"], "1.0")
                self.assertEqual(api._fetch_licenses("pypi", name, requested), (["MIT"], None))

    def test_release_boundaries_are_not_relaxed(self):
        for version in ("1.0rc1", "1.0.dev1", "1.0.post1", "1!1.0", "1.0+local", "1.0.1", "*", "", None):
            with self.subTest(version=version):
                self.assertFalse(same_version("pypi", "1.0", version))
        self.assertFalse(same_version("pypi", "nonsense", "nonsense"))
        for system in ("npm", "go", "maven", "cargo", "nuget", "rubygems"):
            self.assertFalse(same_version(system, "1.0", "1.0.0"))
        self.assertTrue(same_version("pypi", "1.0RC1", "1.0rc1"))

    def test_wrong_or_missing_identity_cannot_supply_license_evidence(self):
        for key in (
            {"name": "other", "version": "1"},
            {"version": "1"},
            {"name": "demo", "version": "1", "system": "NPM"},
            {"name": "demo", "version": "1.0rc1"},
        ):
            with (
                self.subTest(key=key),
                fixtures.fake(
                    {
                        fixtures.PKG("pypi", "demo"): {},
                        fixtures.VER("pypi", "demo", "1"): {"versionKey": key, "licenses": ["MIT"]},
                    }
                ),
            ):
                self.assertIn("error", json.loads(api._run(api._lookup_package, "pypi", "demo", "1")))
                licenses, error = api._fetch_licenses("pypi", "demo", "1")
                self.assertIsNone(licenses)
                self.assertIsNotNone(error)

    def test_registry_equivalent_version_is_found_but_other_releases_are_not(self):
        for returned, status in (("1.0.0", "found"), ("1.0rc1", "unverified"), (None, "unverified")):
            result = check_registry(
                "pypi",
                "Demo_Package",
                "1.0",
                lambda url: fixtures.FakeResp(200, {"info": {"name": "demo-package", "version": returned}}),
            )
            self.assertEqual(result["status"], status)

    def test_graph_and_policy_accept_only_same_pypi_release(self):
        data = clean()
        for key in ("target", "lookup_package"):
            data[key].update(system="pypi", name="Demo_Package", version="1.0")
        data["lookup_package"].update(name="demo-package", version="1.0.0")
        data["get_dependencies"].update(version="1.0.0")
        data["get_dependencies"]["nodes"][0].update(name="demo-package", version="1.0.0")
        self.assertEqual(evaluate(data)["overall"], "allow")
        for version in ("1.0rc1", "1.0.post1", "2.0"):
            changed = copy.deepcopy(data)
            changed["get_dependencies"]["nodes"][0]["version"] = version
            self.assertNotEqual(evaluate(changed)["overall"], "allow")

    def test_requirements_accept_pep440_exact_versions_not_ranges(self):
        text = "demo==1.0rc1\na==1!2.0.post1\nb==2.0.dev1\nc==1.0+local\nd==1.*\ne>=1\nf==1,!=1.2"
        rows = api.parse_manifest(text, "requirements.txt")
        self.assertEqual([r["name"] for r in rows if r["pinned"]], ["demo", "a", "b", "c"])
