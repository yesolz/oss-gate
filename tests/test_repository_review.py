"""Repository regressions for exact identity, coverage, privacy and immutable evidence."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/oss-gate"))
sys.path.insert(0, str(ROOT / "tests"))
import legacy_server
from core import api, yarn
from core.repo_review import collect_repository, discover, _osv, evaluate_repository
from core.repo_render import render_repository
from core.settings import policy_scope, PolicyBlocked, guard_request
from core.snapshot import verify

LOCK = """# Yarn Berry fixture
__metadata:
  version: 8
  cacheKey: 10c0
"demo@workspace:.":
  version: 0.0.0-use.local
  resolution: "demo@workspace:."
  dependencies:
    app: "workspace:*"
    shared: "npm:^1.0.0"
"app@workspace:*, app@workspace:apps/web":
  version: 0.0.0-use.local
  resolution: "app@workspace:apps/web"
  dependencies:
    shared: "npm:^1.0.0"
    alias: "npm:real@^2.0.0"
"shared@npm:^1.0.0":
  version: 1.2.3
  resolution: "shared@npm:1.2.3"
  dependencies:
    child: "npm:3.0.0"
"alias@npm:real@^2.0.0":
  version: 2.1.0
  resolution: "real@npm:2.1.0"
"child@npm:3.0.0":
  version: 3.0.0
  resolution: "child@npm:3.0.0"
"""
MANIFESTS = {
    ".": {
        "name": "demo",
        "private": True,
        "workspaces": ["apps/*"],
        "dependencies": {"app": "workspace:*", "shared": "^1.0.0"},
    },
    "apps/web": {"name": "app", "dependencies": {"shared": "^1.0.0", "alias": "npm:real@^2.0.0"}},
}


def repo(path, lock=LOCK, manifests=None):
    path.mkdir(parents=True, exist_ok=True)
    (path / "yarn.lock").write_text(lock, encoding="utf-8")
    for directory, data in (manifests or MANIFESTS).items():
        target = path / directory / "package.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data), encoding="utf-8")
    return path


def routes(vulnerable=False):
    out = {legacy_server.QB: legacy_server.qb_echo(("GHSA-fixture",) if vulnerable else ())}
    for name, version in (("shared", "1.2.3"), ("real", "2.1.0"), ("child", "3.0.0")):
        out[legacy_server.VER("npm", name, version)] = {
            "versionKey": {"system": "NPM", "name": name, "version": version},
            "licenses": ["MIT"],
            "publishedAt": "2020-01-01T00:00:00Z",
            "raw_extra": "full evidence retained",
        }
    if vulnerable:
        out[legacy_server.ADV("GHSA-fixture")] = {"advisoryKey": {"id": "GHSA-fixture"}, "cvss3Score": 9.8}
        out[legacy_server.OSVV("GHSA-fixture")] = {
            "id": "GHSA-fixture",
            "aliases": ["CVE-fixture"],
            "summary": "<script>alert(1)</script>",
        }
    return out


class YarnInventory(unittest.TestCase):
    def test_invalid_versions_and_source_urls_are_never_npm_identities(self):
        for value in ("1.2", "^1.2.3", "1.2.3-a.", "1.2.3-01", "1.2.3-a..b"):
            self.assertIsNone(yarn.identity("pkg@npm:" + value))
        self.assertEqual(yarn.identity("@scope/pkg@npm:1.2.3-rc.1+build.2")["version"], "1.2.3-rc.1+build.2")
        extra = '\n"pkg@https://user:secret@example.com/archive.tgz":\n  resolution: "pkg@https://user:secret@example.com/archive.tgz"\n'
        result = yarn.analyze(LOCK + extra, MANIFESTS, "yarn.lock")
        self.assertNotIn("secret", json.dumps(result))
        self.assertEqual(result["unresolved"][0]["dependency"], "pkg")
        self.assertEqual(result["unresolved"][0]["source_type"], "https")

    def test_workspaces_aliases_transitive_and_scopes(self):
        result = yarn.analyze(LOCK, MANIFESTS, "yarn.lock")
        self.assertEqual(result["coverage_gaps"], [])
        by_name = {p["name"]: p for p in result["packages"]}
        self.assertEqual(set(by_name), {"real", "shared", "child"})
        self.assertEqual(by_name["real"]["version"], "2.1.0")
        self.assertEqual(by_name["real"]["direct_uses"][0]["declared_name"], "alias")
        self.assertEqual(set(by_name["child"]["projects"]), {"package.json", "apps/web/package.json"})
        self.assertEqual(by_name["child"]["direct_uses"], [])

    def test_stale_missing_and_unsupported_sources_never_clean(self):
        changed = copy.deepcopy(MANIFESTS)
        changed["apps/web"]["dependencies"]["shared"] = "^9.0.0"
        cases = [
            (LOCK, changed, "manifest_lock_mismatch"),
            (LOCK, {".": MANIFESTS["."]}, "workspace_manifest_missing"),
            (
                LOCK
                + '\n"modified@patch:real@npm%3A2.1.0#./fix.patch":\n  resolution: "modified@patch:real@npm%3A2.1.0#./fix.patch"\n',
                MANIFESTS,
                "unsupported_dependency_source",
            ),
            (LOCK.replace('    child: "npm:3.0.0"', '    child: "npm:4.0.0"'), MANIFESTS, "unresolved_lock_edge"),
            (
                LOCK.replace(
                    '  resolution: "child@npm:3.0.0"',
                    '  resolution: "child@npm:3.0.0"\n  peerDependencies:\n    peer: "*"',
                ),
                MANIFESTS,
                "peer_bindings_unverified",
            ),
        ]
        for text, manifests, expected in cases:
            with self.subTest(expected=expected):
                self.assertIn(
                    expected, {g["code"] for g in yarn.analyze(text, manifests, "yarn.lock")["coverage_gaps"]}
                )

    def test_untrusted_yaml_and_classic_are_rejected(self):
        for text in (
            'foo@^1:\n  version "1.0.0"',
            "__metadata: {version: 99}",
            '__metadata: {version: 8}\nx: &a {resolution: "x@npm:1.0.0"}\ny: *a',
            '__metadata: {version: 8}\nx: !!python/object/apply:os.system ["echo bad"]',
            "__metadata: {version: 8}\nx: {}\nx: {}",
            '__metadata: {version: 8}\nx: {resolution: "x@workspace:../outside"}',
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                yarn.analyze(text, MANIFESTS, "yarn.lock")

    def test_discovery_nested_roots_and_unsupported_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = repo(Path(tmp) / "project")
            repo(root / "separate")
            (root / "requirements.txt").write_text("example==1.0.0\n")
            (root / "poetry.lock").write_text("# unsupported\n")
            (root / "node_modules").mkdir()
            (root / "node_modules/package.json").write_text("invalid")
            inventory = discover(root)
            self.assertEqual(len(inventory["projects"]), 4)
            self.assertEqual(len(inventory["packages"]), 3)
            self.assertTrue(all(len(p["occurrences"]) == 2 for p in inventory["packages"]))
            self.assertEqual(
                {g["source"] for g in inventory["coverage_gaps"] if g["code"] == "unsupported_format"},
                {"requirements.txt", "poetry.lock"},
            )
            self.assertFalse(any(f["path"].startswith("node_modules/") for f in inventory["files"]))
            self.assertFalse(inventory["network_performed"])
            self.assertTrue(all(len(f["sha256"]) == 64 for f in inventory["files"]))

    def test_symlinks_limits_and_bad_json_preserve_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = repo(Path(tmp) / "project")
            (root / "escape").symlink_to(Path(tmp), target_is_directory=True)
            (root / "go.mod").symlink_to(Path(tmp) / "secret")
            (root / "apps/web/package.json").write_text('{"dependencies": {}, "dependencies": {}}')
            inventory = discover(root)
            codes = {g["code"] for g in inventory["coverage_gaps"]}
            self.assertTrue(
                {"symlink_skipped", "file_unreadable_or_limited", "invalid_manifest", "workspace_manifest_missing"}
                <= codes
            )
            with patch("core.repo_review.MAX_FILE_BYTES", 20):
                self.assertTrue(discover(root)["coverage_gaps"])
            with patch("core.repo_review.MAX_FILES", 2):
                self.assertIn("discovery_limit", {g["code"] for g in discover(root)["coverage_gaps"]})
            with patch("core.repo_review.MAX_TOTAL_BYTES", 20):
                self.assertIn("discovery_limit", {g["code"] for g in discover(root)["coverage_gaps"]})


class RepositoryCollection(unittest.TestCase):
    def test_identity_mismatch_and_unscored_findings_cannot_approve(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = repo(Path(tmp) / "repo")
            fixture = routes()
            fixture[legacy_server.VER("npm", "shared", "1.2.3")]["versionKey"]["name"] = "wrong-package"
            with legacy_server.fake(fixture):
                result = collect_repository(root, str(Path(tmp) / "output"), True)
            self.assertNotEqual(result["verdict"], "allow")
            self.assertEqual(result["summary"]["license_metadata_available"], 2)
            fixture = routes(True)
            fixture[legacy_server.ADV("GHSA-fixture")]["cvss3Score"] = 0
            with legacy_server.fake(fixture):
                result = collect_repository(root, str(Path(tmp) / "output"), True)
            self.assertEqual(result["verdict"], "conditional")

    def test_selected_additional_rules_are_applied_per_package(self):
        config = {
            "schema": "oss-gate.settings/1",
            "name": "communication",
            "version": "1",
            "review": {"require_communication_review": True, "minimum_release_age_days": 3650},
        }
        with tempfile.TemporaryDirectory() as tmp, policy_scope(config), legacy_server.fake(routes()):
            result = collect_repository(repo(Path(tmp) / "repo"), str(Path(tmp) / "output"), True)
            self.assertEqual(result["verdict"], "conditional")
            data = json.loads(Path(result["data"]).read_text(encoding="utf-8"))
            for p in data["verdict"]["packages"]:
                self.assertIn("communication_unverified", p["verdict"]["coverage_gaps"])
                self.assertIn("release_wait", {f["code"] for f in p["verdict"]["findings"]})

    def test_public_confirmation_before_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = repo(Path(tmp) / "repo")
            with (
                patch.object(api, "_post", side_effect=AssertionError("network")),
                patch.object(api, "_get", side_effect=AssertionError("network")),
            ):
                result = collect_repository(root, str(Path(tmp) / "output"))
            self.assertEqual(result["code"], "public_identifiers_required")
            self.assertFalse((Path(tmp) / "output").exists())

    def test_collect_deduplicates_queries_and_preserves_raw_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = repo(Path(tmp) / "repo")
            with legacy_server.fake(routes()) as fake:
                result = collect_repository(root, str(Path(tmp) / "output"), True)
            self.assertEqual(result["verdict"], "allow")
            self.assertEqual(result["summary"]["packages"], 3)
            query = next(call[2] for call in fake.calls if call[1] == legacy_server.QB)
            self.assertEqual(
                {(p["package"]["name"], p["version"]) for p in query["queries"]},
                {("real", "2.1.0"), ("shared", "1.2.3"), ("child", "3.0.0")},
            )
            self.assertEqual(len(query["queries"]), 3)
            folder = Path(result["folder"])
            verify(folder)
            self.assertIn("full evidence retained", (folder / "api-responses.json").read_text(encoding="utf-8"))

    def test_vulnerability_aliases_count_once_and_reports_escape(self):
        with tempfile.TemporaryDirectory() as tmp, legacy_server.fake(routes(True)):
            result = collect_repository(repo(Path(tmp) / "repo"), str(Path(tmp) / "output"), True)
            self.assertEqual(result["verdict"], "hold")
            self.assertEqual(result["summary"]["advisory_groups"], 1)
            self.assertEqual(result["summary"]["affected_packages"], 3)
            rendered = render_repository(result["folder"], "both")
            self.assertEqual(len(rendered["files"]), 4)
            folder = Path(result["folder"])
            for lang in ("ko", "en"):
                html = (folder / f"report.{lang}.html").read_text(encoding="utf-8")
                self.assertNotIn("<script>alert(1)</script>", html)
                self.assertIn("GHSA-fixture", html)
                self.assertIn("Content-Security-Policy", html)
            (folder / "data.json").write_text("{}")
            with self.assertRaises(ValueError):
                render_repository(folder)

    def test_unknown_caps_and_other_ecosystems_cannot_approve(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = repo(Path(tmp) / "repo")
            with legacy_server.fake(routes()):
                capped = collect_repository(root, str(Path(tmp) / "output"), True, 1)
            self.assertNotEqual(capped["verdict"], "allow")
            self.assertEqual(capped["summary"]["vulnerability_queries_complete"], 1)
            (root / "Cargo.lock").write_text("version = 3\n")
            with legacy_server.fake(routes()):
                mixed = collect_repository(root, str(Path(tmp) / "output"), True)
            self.assertEqual(mixed["verdict"], "conditional")
            failed = routes()
            failed[legacy_server.QB] = (503, {})
            with legacy_server.fake(failed):
                result = collect_repository(root, str(Path(tmp) / "output"), True)
            self.assertNotEqual(result["verdict"], "allow")
            self.assertEqual(result["summary"]["vulnerability_queries_complete"], 0)

    def test_policy_allowlist_excludes_private_names_and_applies_restrictions(self):
        config = {
            "schema": "oss-gate.settings/1",
            "name": "Explicit",
            "version": "1",
            "network": {"allow_identifiers": ["npm:shared"]},
            "review": {"license_restrictions": {"MIT": "hold"}},
        }
        with tempfile.TemporaryDirectory() as tmp, legacy_server.fake(routes()) as fake, policy_scope(config):
            result = collect_repository(repo(Path(tmp) / "repo"), str(Path(tmp) / "output"))
            self.assertEqual(result["verdict"], "hold")
            self.assertEqual(result["summary"]["vulnerability_queries_complete"], 1)
            sent = [
                p["package"]["name"] for call in fake.calls if call[1] == legacy_server.QB for p in call[2]["queries"]
            ]
            self.assertEqual(sent, ["shared"])
            data = json.loads(Path(result["data"]).read_text(encoding="utf-8"))
            self.assertEqual(evaluate_repository(data), data["verdict"])

    def test_osv_pagination_and_policy_guard(self):
        package = [{"system": "npm", "name": "shared", "version": "1.2.3"}]
        with legacy_server.fake(
            {
                legacy_server.QB: {"results": [{"vulns": [{"id": "A"}], "next_page_token": "next"}]},
                api.OSV_BASE + "/query": {"vulns": [{"id": "B"}]},
            }
        ):
            self.assertEqual(_osv(package), [{"ids": ["A", "B"], "complete": True}])
        with legacy_server.fake(
            {
                legacy_server.QB: {"results": [{"vulns": [{"id": "A"}], "next_page_token": "next"}]},
                api.OSV_BASE + "/query": {"vulns": [], "next_page_token": "next"},
            }
        ):
            self.assertEqual(_osv(package), [{"ids": ["A"], "complete": False}])
        config = {
            "schema": "oss-gate.settings/1",
            "name": "deny",
            "version": "1",
            "network": {"deny_identifiers": ["npm:secret"]},
        }
        with policy_scope(config), self.assertRaises(PolicyBlocked):
            guard_request(
                api.OSV_BASE + "/query",
                {"package": {"ecosystem": "npm", "name": "secret"}, "version": "1", "page_token": "next"},
            )

    def test_cli_plan_does_not_collect(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = repo(Path(tmp) / "repo")
            result = subprocess.run(
                [sys.executable, str(ROOT / "plugins/oss-gate/cli.py"), "repo-plan", str(root)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(json.loads(result.stdout)["network_performed"])


if __name__ == "__main__":
    unittest.main()
