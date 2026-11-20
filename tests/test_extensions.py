"""Optional rules must preserve defaults, prevent egress and never erase uncertainty."""

import asyncio
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/oss-gate"
sys.path.insert(0, str(PLUGIN))
import cli
import legacy_server
from test_review import clean
from core import api, deepwiki
from core.additional_policy import validate_communication
from core.policy import evaluate
from core.portfolio import aggregate, compare
from core.render import render
from core.service import invoke
from core.settings import fingerprint, load_policy, policy_scope, validate
from core.snapshot import load_review, seal, write_json


def settings(**review):
    return {"schema": "oss-gate.settings/1", "name": "Example policy", "version": "1", "review": review}


def with_policy(data, config):
    data = copy.deepcopy(data)
    data["generated_at"] = "2026-11-20T00:00:00+00:00"
    data["policy_context"] = {
        "schema": "oss-gate.policy-context/1",
        "config": config,
        "sha256": fingerprint(config),
        "evaluated_at": data["generated_at"],
    }
    return data


def facts():
    return {
        "schema": "oss-gate.communication/1",
        "target": clean()["target"],
        "status": "reviewed",
        "coverage": "complete",
        "reviewed_by": "Test reviewer",
        "reviewed_at": "2026-11-19T00:00:00Z",
        "sources": ["https://example.org/docs"],
        "observations": [
            {
                "destination": "https://telemetry.example.org/events",
                "data": "usage counters",
                "purpose": "telemetry",
                "default_enabled": True,
                "required": False,
                "can_disable": True,
            }
        ],
    }


def routes():
    return {
        legacy_server.PKG("npm", "demo"): {"versions": []},
        legacy_server.VER("npm", "demo", "1.0.0"): {
            "versionKey": {"name": "demo", "version": "1.0.0"},
            "licenses": ["MIT"],
            "publishedAt": "2026-11-19T00:00:00Z",
        },
        legacy_server.DEPS("npm", "demo", "1.0.0"): {
            "nodes": [{"versionKey": {"name": "demo", "version": "1.0.0"}, "relation": "SELF"}],
        },
        legacy_server.QB: legacy_server.qb_echo(()),
    }


class ExtensionTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {}, clear=False)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("OSS_GATE_POLICY", None)

    def test_default_policy_and_html_remain_unchanged(self):
        data = clean()
        verdict = evaluate(data)
        self.assertEqual(verdict["overall"], "allow")
        self.assertNotIn("additional_policy", verdict)
        for lang in ("ko", "en"):
            self.assertNotIn('id="additional-policy"', render(data, "", lang))

    def test_policy_loading_is_explicit_and_launch_policy_cannot_be_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "policy.json"
            p.write_text(json.dumps(settings()))
            self.assertIsNone(load_policy())
            os.environ["OSS_GATE_POLICY"] = str(p)
            self.assertEqual(load_policy()["name"], "Example policy")
            with self.assertRaises(ValueError):
                load_policy(str(Path(tmp) / "other.json"))
            p.write_text('{"schema":"unknown"}')
            with legacy_server.fake({}) as http:
                result = json.loads(invoke("lookup_package", "npm", "demo", "1.0.0"))
            self.assertEqual(result["code"], "policy_invalid")
            self.assertEqual(http.calls, [])

    def test_invalid_settings_fail_closed(self):
        for change in [
            {"network": {"services": ["typo"]}},
            {"network": {"allow_identifiers": "*"}},
            {"network": {"deny_identifiers": ["demo"]}},
            {"review": {"minimum_release_age_days": True}},
            {"review": {"minimum_release_age_days": -1}},
            {"review": {"require_communication_review": "yes"}},
            {"review": {"blocked_destinations": ["https://example.org"]}},
            {"review": {"typo": 1}},
        ]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate({**settings(), **change})

    def test_denied_names_are_blocked_before_every_http_path(self):
        config = {
            **settings(),
            "network": {"deny_identifiers": ["npm:@internal/*", "pypi:Private_Pkg", "repo:company/*"]},
        }
        urls = [
            (legacy_server.PKG("npm", "@internal/secret"), None),
            ("https://registry.npmjs.org/%40internal%2Fsecret/1.0.0", None),
            ("https://pypi.org/pypi/private-pkg/1.0.0/json", None),
            (api.DEPSDEV_BASE + "/projects/github.com%2Fcompany%2Fsecret", None),
            (
                legacy_server.QB,
                {"queries": [{"package": {"ecosystem": "PyPI", "name": "private.pkg"}, "version": "1"}]},
            ),
        ]
        with policy_scope(config), legacy_server.fake({}) as http:
            for url, body in urls:
                with self.subTest(url=url), self.assertRaises(api.ApiError) as error:
                    api._request("POST" if body else "GET", url, body)
                self.assertEqual(error.exception.extra["code"], "policy_blocked")
                self.assertNotIn("secret", str(error.exception))
            self.assertEqual(http.calls, [])

    def test_allowlist_deny_wins_and_scope_does_not_leak(self):
        config = {**settings(), "network": {"allow_identifiers": ["npm:*"], "deny_identifiers": ["npm:demo"]}}
        with policy_scope(config), legacy_server.fake({}) as http:
            result = json.loads(api._run(api._lookup_package, "npm", "demo", "1.0.0"))
            self.assertEqual(result["code"], "policy_blocked")
            self.assertEqual(http.calls, [])
        with legacy_server.fake(routes()) as http:
            self.assertEqual(json.loads(invoke("lookup_package", "npm", "demo", "1.0.0"))["name"], "demo")
            self.assertTrue(http.calls)

    def test_worker_requests_and_osv_batches_respect_policy(self):
        fixtures = routes()
        fixtures[legacy_server.DEPS("npm", "demo", "1.0.0")]["nodes"].append(
            {"versionKey": {"name": "@internal/secret", "version": "1.0.0"}, "relation": "DIRECT"}
        )
        config = {**settings(), "network": {"deny_identifiers": ["npm:@internal/*"]}}
        with policy_scope(config), legacy_server.fake(fixtures) as http:
            graph = api._get_dependencies("npm", "demo", "1.0.0", True, True, 200)
        self.assertTrue(graph["osv_incomplete"])
        self.assertTrue(graph["license_lookup_failures"])
        self.assertFalse(any("internal" in json.dumps(call) for call in http.calls))

    def test_release_time_boundaries_and_unknown_never_approve(self):
        config = settings(minimum_release_age_days=7)
        for date, outcome in [
            ("2026-11-13T00:00:00Z", "allow"),
            ("2026-11-13T00:00:01Z", "conditional"),
            ("2026-11-13T09:00:00+09:00", "allow"),
            (None, "conditional"),
            ("bad", "conditional"),
            ("2026-11-21T00:00:00Z", "conditional"),
            ("2026-11-13T00:00:00", "conditional"),
        ]:
            with self.subTest(date=date):
                data = with_policy(clean(), config)
                data["lookup_package"]["published_at"] = date
                self.assertEqual(evaluate(data)["overall"], outcome)
        data["lookup_package"]["licenses"] = ["GPL-3.0-only"]
        self.assertEqual(evaluate(data)["overall"], "hold")
        data["policy_context"]["config"]["review"]["minimum_release_age_days"] = 0
        with self.assertRaises(ValueError):
            evaluate(data)

    def test_communication_requires_attributed_matching_evidence(self):
        config = settings(require_communication_review=True, blocked_destinations=["*.example.org"])
        data = with_policy(clean(), config)
        self.assertEqual(evaluate(data)["overall"], "conditional")
        data["communication"] = facts()
        self.assertEqual(evaluate(data)["overall"], "hold")
        data["communication"]["observations"][0]["default_enabled"] = False
        self.assertEqual(evaluate(data)["overall"], "allow")
        for key, value in [
            ("status", "unverified"),
            ("coverage", "partial"),
            ("reviewed_at", "2026-11-21T00:00:00Z"),
            ("sources", []),
            ("reviewed_by", ""),
            ("target", {**clean()["target"], "version": "2.0.0"}),
        ]:
            with self.subTest(key=key):
                candidate = copy.deepcopy(data)
                candidate["communication"][key] = value
                self.assertEqual(evaluate(candidate)["overall"], "conditional")
        data["communication"]["observations"][0]["required"] = None
        self.assertEqual(evaluate(data)["overall"], "conditional")

    def test_communication_schema_rejects_malformed_flags_and_credentials(self):
        for value in ["true", 0, 1]:
            item = facts()
            item["observations"][0]["required"] = value
            with self.assertRaises(ValueError):
                validate_communication(item)
        item = facts()
        item["sources"] = ["https://user:password@example.org"]
        with self.assertRaises(ValueError):
            validate_communication(item)

    def test_communication_cannot_imply_none_from_an_omitted_list(self):
        item = facts()
        del item["observations"]
        with self.assertRaises(ValueError):
            validate_communication(item)
        data = with_policy(clean(), settings(require_communication_review=True))
        data["communication"] = facts()
        data["communication"]["observations"][0]["can_disable"] = None
        self.assertEqual(evaluate(data)["overall"], "conditional")
        data["communication"]["observations"] = []
        self.assertEqual(evaluate(data)["overall"], "allow")

    def test_destination_matching_handles_dns_case_and_trailing_dot(self):
        data = with_policy(clean(), settings(blocked_destinations=["telemetry.example.org"]))
        data["communication"] = facts()
        data["communication"]["observations"][0]["destination"] = "https://TELEMETRY.EXAMPLE.ORG./events"
        self.assertEqual(evaluate(data)["overall"], "hold")
        data["communication"]["observations"][0]["destination"] = "http://telemetry.example.org/events"
        self.assertEqual(evaluate(data)["overall"], "hold")
        data["communication"]["observations"][0]["destination"] = "https://%74elemetry.example.org/events"
        self.assertEqual(evaluate(data)["overall"], "conditional")
        data["communication"]["observations"][0]["destination"] = "https://telemetry.example.org/events"
        data["communication"]["reviewed_at"] = "0001-01-01T00:00:00+14:00"
        self.assertEqual(evaluate(data)["overall"], "conditional")

    def test_cli_and_mcp_share_saved_policy_and_verdict(self):
        spec = importlib.util.spec_from_file_location("deps_adapter", PLUGIN / "mcp/depsdev/server.py")
        adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adapter)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "settings.json"
            p.write_text(json.dumps(settings(minimum_release_age_days=3650)))
            os.environ["OSS_GATE_POLICY"] = str(p)
            with legacy_server.fake(routes()):
                mcp = json.loads(adapter.collect_review("npm", "demo", "1.0.0", output_root=tmp))
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    code = cli.main(["collect", "npm", "demo", "--version", "1.0.0", "--output-root", tmp])
            result = json.loads(stdout.getvalue())
            self.assertEqual(code, 0)
            self.assertEqual(result["verdict"]["overall"], mcp["verdict"]["overall"])
            data = load_review(result["data"])
            self.assertEqual(evaluate(data), result["verdict"])
            self.assertEqual(data["policy_context"]["sha256"], fingerprint(settings(minimum_release_age_days=3650)))
            for lang, expected in [("ko", "추가 정책 적용 후"), ("en", "With selected policy")]:
                self.assertIn(expected, render(data, "", lang))

    def test_disabled_osv_retains_unknown_and_policy_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "settings.json"
            p.write_text(json.dumps({**settings(), "network": {"services": ["depsdev"]}}))
            with legacy_server.fake(routes()) as http:
                result = json.loads(
                    invoke("collect_review", "npm", "demo", "1.0.0", output_root=tmp, policy_path=str(p))
                )
            self.assertNotEqual(result["verdict"]["overall"], "allow")
            self.assertIn("policy_limited_collection", result["verdict"]["coverage_gaps"])
            self.assertFalse(any("osv.dev" in call[1] for call in http.calls))

    def test_plan_is_offline_and_deepwiki_checks_before_connect(self):
        config = {**settings(), "network": {"services": ["depsdev", "osv"]}}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "settings.json"
            p.write_text(json.dumps(config))
            with legacy_server.fake({}) as http:
                result = json.loads(invoke("plan", "npm", "demo", "1.0.0", "owner/repo", policy_path=str(p)))
            self.assertFalse(result["network_performed"])
            self.assertEqual(http.calls, [])
            with patch.object(deepwiki, "streamablehttp_client") as connect:
                result = asyncio.run(deepwiki.request("owner/repo", policy_path=str(p)))
                self.assertEqual(result["code"], "policy_blocked")
                connect.assert_not_called()
                result = asyncio.run(deepwiki.request("owner/repo", topic="our internal secret"))
                self.assertEqual(result["code"], "invalid_input")
                connect.assert_not_called()

    def test_portfolio_cannot_mix_additional_policies(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for index, days in enumerate((1, 7)):
                folder = Path(tmp) / str(index)
                folder.mkdir()
                write_json(folder / "data.json", with_policy(clean(), settings(minimum_release_age_days=days)))
                seal(folder, ["data.json"])
                paths.append(folder)
            with self.assertRaises(ValueError):
                aggregate(paths)
            with self.assertRaises(ValueError):
                compare(aggregate(paths[:1]), aggregate(paths[1:]))


if __name__ == "__main__":
    unittest.main()
