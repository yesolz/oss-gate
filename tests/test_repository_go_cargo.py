"""Go/Cargo regressions for source identity, uncertainty and mixed-ecosystem evidence."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/oss-gate"))
sys.path.insert(0, str(ROOT / "tests"))
import legacy_server
from core import cargo, gomod
from core.repo_review import collect_repository, discover
from core.repo_render import render_repository, GAPS
from core.settings import policy_scope
from test_repository_review import repo, routes

CARGO_ROOT = """[workspace]
members = ["crates/*"]
resolver = "2"
[workspace.package]
version = "0.1.0"
[workspace.dependencies]
alias = { package = "shared", version = "1.2" }
"""
CARGO_APP = """[package]
name = "demo"
version.workspace = true
[dependencies]
alias.workspace = true
[target.'cfg(unix)'.build-dependencies]
child = "3"
"""
CARGO_LOCK = """version = 4
[[package]]
name = "demo"
version = "0.1.0"
dependencies = ["shared", "child"]
[[package]]
name = "shared"
version = "1.2.3"
source = "registry+https://github.com/rust-lang/crates.io-index"
dependencies = ["child"]
[[package]]
name = "child"
version = "3.0.0"
source = "registry+https://github.com/rust-lang/crates.io-index"
"""


def cargo_inputs():
    return {"rust/Cargo.toml": CARGO_ROOT, "rust/crates/demo/Cargo.toml": CARGO_APP, "rust/Cargo.lock": CARGO_LOCK}


def write(root, contents):
    for name, value in contents.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)


def codes(result):
    return {g["code"] for g in result["coverage_gaps"]}


class GoInventory(unittest.TestCase):
    def test_requirements_not_checksums_and_replacements_preserve_identity(self):
        inputs = {
            "go.mod": """module example.org/app
go 1.23
require (
 "example.org/direct" v1.2.3
 example.org/indirect v0.0.0-20240101010101-abcdef123456 // indirect
 example.org/local v2.0.0
 example.org/excluded v1.0.0
)
replace (
 example.org/direct => example.org/fork v1.4.0
 example.org/local => ../private-token
)
exclude example.org/excluded v1.0.0
""",
            "go.sum": "example.org/unused v9.0.0 h1:old\n",
        }
        result = gomod.analyze(inputs)
        self.assertEqual(
            {(p["name"], p["version"]) for p in result["packages"]},
            {
                ("example.org/fork", "v1.4.0"),
                ("example.org/indirect", "v0.0.0-20240101010101-abcdef123456"),
            },
        )
        self.assertEqual(len(result["projects"][0]["direct_dependencies"]), 1)
        self.assertEqual(result["projects"][0]["direct_dependencies"][0]["declared_name"], "example.org/direct")
        self.assertTrue(
            {"go_build_list_unverified", "go_local_replacement", "go_requirement_unresolved"} <= codes(result)
        )
        self.assertNotIn("private-token", json.dumps(result))
        self.assertEqual(result["statuses"]["go.sum"], "checksum_only")

    def test_workspace_overrides_conflicts_and_local_members(self):
        inputs = {
            "go.work": "go 1.23\nuse (\n ./a\n ./b\n)\nreplace example.org/lib => example.org/workfork v3.0.0\n",
            "a/go.mod": "module example.org/a\nrequire example.org/lib v1.0.0\nreplace example.org/lib => example.org/fork1 v1.0.0\n",
            "b/go.mod": "module example.org/b\nrequire (\nexample.org/lib v2.0.0\nexample.org/a v1.0.0\n)\nreplace example.org/lib => example.org/fork2 v2.0.0\n",
        }
        result = gomod.analyze(inputs)
        self.assertEqual({p["name"] for p in result["packages"]}, {"example.org/workfork"})
        self.assertNotIn("go_requirement_unresolved", codes(result))
        inputs["go.work"] = "go 1.23\nuse (\n ./a\n ./b\n)\n"
        result = gomod.analyze(inputs)
        self.assertFalse(result["packages"])
        self.assertIn("go_requirement_unresolved", codes(result))

    def test_missing_or_invalid_workspace_cannot_query_unreplaced_modules(self):
        base = {"a/go.mod": "module example.org/a\nrequire example.org/private v1.0.0\n"}
        for work in (
            "use (\n./a\n../outside\n)\n",
            "replace invalid",
            "use ./a\nreplace example.org/private => https://user:token@host\n",
        ):
            with self.subTest(work=work):
                result = gomod.analyze({**base, "go.work": work})
                self.assertFalse(result["packages"])
                self.assertTrue(result["coverage_gaps"])
                self.assertNotIn("token@host", json.dumps(result))

    def test_invalid_or_duplicate_directives_do_not_emit_versions(self):
        for text in (
            "require example.org/lib latest",
            "require example.org/lib v1.0",
            "require example.org/lib v1.0.0\nrequire example.org/lib v2.0.0",
            "replace example.org/lib => example.org/fork v1.0.0\nreplace example.org/lib => ./local",
            'require "unterminated v1.0.0',
            "unknown thing",
            "require (\nexample.org/lib v1.0.0",
        ):
            with self.subTest(text=text):
                result = gomod.analyze({"go.mod": "module example.org/app\n" + text})
                self.assertFalse(result["packages"])
                self.assertIn("go_manifest_invalid", codes(result))


class CargoInventory(unittest.TestCase):
    def test_invalid_dependency_tables_cannot_be_treated_as_wildcards(self):
        for spec in ("{}", "{workspace=false}", "{optional=true}", "{version=1}", '{version="1",features=true}'):
            inputs = cargo_inputs()
            inputs["rust/crates/demo/Cargo.toml"] = CARGO_APP.replace("alias.workspace = true", "alias = " + spec)
            self.assertIn("invalid_manifest_dependency", codes(cargo.analyze(inputs)))

    def test_workspace_alias_inheritance_target_and_transitive(self):
        result = cargo.analyze(cargo_inputs())
        self.assertEqual(result["coverage_gaps"], [])
        self.assertEqual(len(result["projects"]), 1)
        dependencies = result["projects"][0]["direct_dependencies"]
        self.assertEqual(
            {(p["name"], p["version"]) for p in result["packages"]}, {("shared", "1.2.3"), ("child", "3.0.0")}
        )
        self.assertEqual(dependencies[0]["declared_name"], "alias")
        self.assertEqual(dependencies[1]["group"], "target:cfg(unix)/build-dependencies")
        self.assertTrue(all(p["projects"] == ["rust/crates/demo/Cargo.toml"] for p in result["packages"]))

    def test_git_and_private_registry_are_not_public_crates(self):
        for source in ("git+https://user:token@host/repo#abcdef", "registry+https://user:token@host/index"):
            inputs = cargo_inputs()
            inputs["rust/Cargo.lock"] = CARGO_LOCK.replace(
                "registry+https://github.com/rust-lang/crates.io-index", source
            )
            result = cargo.analyze(inputs)
            self.assertFalse(result["packages"])
            self.assertIn("cargo_source_unverified", codes(result))
            self.assertNotIn("token", json.dumps(result))

    def test_path_dependency_is_not_public_package_and_is_traversed(self):
        inputs = {
            "Cargo.toml": '[package]\nname="demo"\nversion="0.1.0"\n[dependencies]\nlocal={path="crates/local"}\n',
            "crates/local/Cargo.toml": '[package]\nname="local"\nversion="0.1.0"\n[dependencies]\nshared="1"\n',
            "Cargo.lock": CARGO_LOCK.replace('dependencies = ["shared", "child"]', 'dependencies = ["local"]')
            + '\n[[package]]\nname="local"\nversion="0.1.0"\ndependencies=["shared"]\n',
        }
        result = cargo.analyze(inputs)
        self.assertEqual(result["coverage_gaps"], [])
        self.assertEqual(len(result["projects"]), 2)
        self.assertNotIn("local", {p["name"] for p in result["packages"]})
        self.assertTrue(all(len(p["projects"]) == 2 for p in result["packages"]))

    def test_stale_manifest_missing_members_ambiguous_edges_and_patches_remain_gaps(self):
        cases = [
            ("rust/Cargo.toml", CARGO_ROOT.replace('version = "1.2"', 'version = "9"'), "manifest_lock_mismatch"),
            ("rust/Cargo.toml", CARGO_ROOT.replace('"crates/*"', '"missing/*"'), "cargo_workspace_member_missing"),
            (
                "rust/Cargo.toml",
                CARGO_ROOT + '\n[patch.crates-io]\nshared={path="../private"}\n',
                "cargo_source_unverified",
            ),
            (
                "rust/Cargo.lock",
                CARGO_LOCK
                + '\n[[package]]\nname="child"\nversion="4.0.0"\nsource="registry+https://github.com/rust-lang/crates.io-index"\n',
                "unresolved_lock_edge",
            ),
            ("rust/Cargo.lock", CARGO_LOCK.replace('"child"]', '"missing"]'), "unresolved_lock_edge"),
            (
                "rust/crates/demo/Cargo.toml",
                CARGO_APP.replace("alias.workspace = true", "unknown.workspace = true"),
                "cargo_inheritance_unresolved",
            ),
        ]
        for path, text, expected in cases:
            with self.subTest(expected=expected):
                inputs = cargo_inputs()
                inputs[path] = text
                self.assertIn(expected, codes(cargo.analyze(inputs)))

    def test_malformed_and_future_lockfiles_cannot_emit_packages(self):
        for lock in (
            CARGO_LOCK.replace("version = 4", "version = 99"),
            CARGO_LOCK
            + '\n[[package]]\nname="child"\nversion="3.0.0"\nsource="registry+https://github.com/rust-lang/crates.io-index"\n',
            'version=4\npackage="invalid"',
            "version=4\nversion=4",
        ):
            result = cargo.analyze({**cargo_inputs(), "rust/Cargo.lock": lock})
            self.assertFalse(result["packages"])
            self.assertTrue(result["coverage_gaps"])

    def test_cargo_ranges_follow_caret_zero_rules_and_preserve_unknown(self):
        for requirement, version, expected in (
            ("1.2", "1.9.0", True),
            ("1.2", "2.0.0", False),
            ("0.2", "0.3.0", False),
            ("0", "0.9.0", True),
            ("0.0", "0.0.9", True),
            ("0.0.3", "0.0.4", False),
            ("~1.2", "1.3.0", False),
            (">=1.2.0, <2.0.0", "1.8.0", True),
            ("1.*", "1.8.0", True),
            ("=1.2.3", "1.2.4", False),
            ("1.0.0-alpha", "1.0.0-alpha", None),
            ("1 || 2", "1.0.0", None),
        ):
            with self.subTest(requirement=requirement, version=version):
                self.assertIs(cargo.requirement_matches(requirement, version), expected)

    def test_excluded_or_outside_path_dependencies_remain_unverified(self):
        inputs = cargo_inputs()
        inputs["rust/crates/demo/Cargo.toml"] += '\n[dev-dependencies]\nprivate={path="../../../private"}\n'
        result = cargo.analyze(inputs)
        self.assertIn("cargo_local_dependency_unverified", codes(result))


class MixedRepository(unittest.TestCase):
    def fixture(self, root):
        repo(root)
        write(root, {**cargo_inputs(), "go/go.mod": "module example.org/app\nrequire example.org/lib v1.0.0\n"})
        fixture = routes()
        for system, name, version in (
            ("cargo", "shared", "1.2.3"),
            ("cargo", "child", "3.0.0"),
            ("go", "example.org/lib", "v1.0.0"),
        ):
            fixture[legacy_server.VER(system, name, version)] = {
                "versionKey": {"system": system.upper(), "name": name, "version": version},
                "licenses": ["MIT"],
            }
        return fixture

    def test_queries_policy_and_render_use_ecosystem_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            fixture = self.fixture(root)
            with legacy_server.fake(fixture) as fake:
                result = collect_repository(root, str(Path(tmp) / "out"), True)
            self.assertEqual(result["summary"]["packages"], 6)
            self.assertEqual(result["summary"]["vulnerability_queries_complete"], 6)
            self.assertEqual(result["summary"]["license_metadata_available"], 6)
            self.assertEqual(result["verdict"], "conditional")
            query = next(call[2] for call in fake.calls if call[1] == legacy_server.QB)
            self.assertEqual({p["package"]["ecosystem"] for p in query["queries"]}, {"npm", "Go", "crates.io"})
            folder = Path(result["folder"])
            render_repository(folder, "both")
            for lang in ("ko", "en"):
                report = (folder / f"report.{lang}.html").read_text()
                for identity in ("npm:shared", "cargo:shared", "go:example.org/lib"):
                    self.assertIn(identity, report)
                self.assertIn("Go", report)
            data = json.loads((folder / "data.json").read_text())
            self.assertEqual(
                next(p for p in data["verdict"]["packages"] if p["system"] == "go")["verdict"]["license_reviews"][0][
                    "relation"
                ],
                "DECLARED",
            )

    def test_cargo_can_allow_scoped_lock_review_and_configuration_cannot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            fixture = self.fixture(root)
            # Isolate Cargo while retaining the same public API fixture.
            root = root / "rust"
            with legacy_server.fake(fixture):
                result = collect_repository(root, str(Path(tmp) / "out"), True)
            self.assertEqual(result["verdict"], "allow")
            write(root, {".cargo/config.toml": '[source.crates-io]\nreplace-with="internal"\n'})
            with legacy_server.fake(fixture):
                result = collect_repository(root, str(Path(tmp) / "out"), True)
            self.assertEqual(result["verdict"], "conditional")

    def test_allowlist_prevents_other_ecosystems_and_private_go_queries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            fixture = self.fixture(root)
            config = {
                "schema": "oss-gate.settings/1",
                "name": "Cargo only",
                "version": "1",
                "network": {"allow_identifiers": ["cargo:shared"]},
            }
            with policy_scope(config), legacy_server.fake(fixture) as fake:
                result = collect_repository(root, str(Path(tmp) / "out"))
            self.assertEqual(result["summary"]["vulnerability_queries_complete"], 1)
            query = next(call[2] for call in fake.calls if call[1] == legacy_server.QB)
            self.assertEqual(
                query["queries"], [{"package": {"ecosystem": "crates.io", "name": "shared"}, "version": "1.2.3"}]
            )
            self.assertFalse(any("example.org" in call[1] for call in fake.calls))
            self.assertNotEqual(result["verdict"], "allow")
            data = json.loads(Path(result["data"]).read_text())
            blocked = [g["package"] for g in data["inventory"]["coverage_gaps"] if g["code"] == "package_policy_blocked"]
            self.assertIn({"system": "npm", "name": "shared", "version": "1.2.3"}, blocked)
            self.assertNotIn({"system": "cargo", "name": "shared", "version": "1.2.3"}, blocked)

    def test_unreadable_workspace_and_checksum_files_preserve_uncertainty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                {"go.mod": "module example.org/app\nrequire example.org/lib v1.0.0\n", "go.work.sum": "old checksum"},
            )
            (root / "go.work").symlink_to(root / "missing")
            result = discover(root)
            self.assertFalse(result["packages"])
            self.assertIn("file_unreadable_or_limited", codes(result))

    def test_all_adapter_gaps_have_both_translations(self):
        for module in (cargo, gomod):
            import inspect
            import re

            names = re.findall(r'gap\("([a-z_]+)"', inspect.getsource(module))
            for name in names:
                self.assertIn(name, GAPS)
                self.assertTrue(all(GAPS[name]))


if __name__ == "__main__":
    unittest.main()
