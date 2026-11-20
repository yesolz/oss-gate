"""Network customization must not leak blocked names or overstate mirror evidence."""

import asyncio
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/oss-gate"))
import cli
import legacy_server
from core import api, deepwiki
from core.repository import normalize_repository
from core.service import invoke
from core.settings import policy_scope, validate
import test_lookup_failures as lookup_fixtures


def policy(**network):
    return {"schema": "oss-gate.settings/1", "name": "Network test", "version": "1", "network": network}


class NetworkOptions(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ)
        env.start()
        os.environ.pop("OSS_GATE_POLICY", None)
        self.addCleanup(env.stop)

    def test_repository_identity_is_not_reinterpreted(self):
        self.assertEqual(normalize_repository("Team.Name/Repo.git"), "github.com/team.name/repo")
        self.assertEqual(normalize_repository("https://GITHUB.COM./Org/Repo.git/"), "github.com/org/repo")
        self.assertEqual(normalize_repository("https://github.com/org/repo/issues"), "github.com/org/repo")
        self.assertEqual(
            normalize_repository("git.example.internal/group/subgroup/repo"), "git.example.internal/group/subgroup/repo"
        )
        for value in (
            "https://user:secret@github.com/o/r",
            "https://github.com:443/o/r",
            "https://github.com/o/%72",
            "https://github.com/o/r?secret=x",
            "https://github.com/o/r#x",
            "https://github.com/o/../r",
            "https://github.com/o//r",
            "https://github.com/o/r/unknown",
            "ssh://git.example/o/r",
            "github.com\\evil/o/r",
            "https://github.com/o/r\nsecret",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_repository(value)

    def test_host_allowlist_and_legacy_deny_apply_before_transport(self):
        cases = [
            (policy(allowed_repository_hosts=["github.com"]), "git.example.internal/company/x"),
            (policy(allowed_repository_hosts=["github.com"]), "https://github.com.evil.test/company/x"),
            (policy(allowed_repository_hosts=[]), "company/x"),
            (policy(deny_identifiers=["repo:company/*"]), "https://GITHUB.COM./Company/x.git"),
            (policy(deny_identifiers=["repo:*.example.internal/*"]), "git.example.internal/company/x"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "policy.json"
            for config, repo in cases:
                p.write_text(json.dumps(config))
                with self.subTest(repo=repo, config=config), legacy_server.fake({}) as http:
                    result = json.loads(invoke("get_project", repo, policy_path=str(p)))
                self.assertEqual(result["code"], "policy_blocked")
                self.assertEqual(http.calls, [])
            # Both project endpoints carry the same repository identity.
            with policy_scope(policy(allow_identifiers=["repo:org/repo"], allowed_repository_hosts=["GITHUB.COM."])):
                from core.settings import guard_request

                for suffix in ("", ":packageversions"):
                    guard_request(api.DEPSDEV_BASE + "/projects/github.com%2Forg%2Frepo" + suffix)
            with policy_scope(policy(deny_identifiers=["repo:org/repo"])), legacy_server.fake({}) as http:
                for suffix in ("", ":packageversions"):
                    with self.assertRaises(api.ApiError):
                        api._request("GET", api.DEPSDEV_BASE + "/projects/github.com%2Forg%2Frepo" + suffix)
                self.assertEqual(http.calls, [])

    def test_discovered_repository_is_guarded(self):
        package = legacy_server.PKG("npm", "demo")
        version = legacy_server.VER("npm", "demo", "1.0.0")
        routes = {
            package: {"versions": []},
            version: {
                "versionKey": {"system": "NPM", "name": "demo", "version": "1.0.0"},
                "relatedProjects": [{"projectKey": {"id": "git.example.internal/company/x"}}],
            },
        }
        with policy_scope(policy(allowed_repository_hosts=["github.com"])), legacy_server.fake(routes) as http:
            result = json.loads(api._run(api._lookup_package, "npm", "demo", "1.0.0"))
        self.assertNotIn("error", result)
        self.assertFalse(any("/projects/" in call[1] for call in http.calls))

    def test_deepwiki_rejects_unsupported_hosts_without_connection(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "policy.json"
            p.write_text(json.dumps(policy(allowed_repository_hosts=["github.com"])))
            with patch.object(deepwiki, "streamablehttp_client") as connect:
                blocked = asyncio.run(deepwiki.request("git.example.internal/org/repo", policy_path=str(p)))
                self.assertEqual(blocked["code"], "policy_blocked")
                unsupported = asyncio.run(deepwiki.request("git.example.internal/org/repo"))
                self.assertEqual(unsupported["code"], "unsupported_repository_host")
                connect.assert_not_called()
            plan = json.loads(invoke("plan", "npm", "demo", "1.0.0", "git.example.internal/org/repo"))
            self.assertEqual(plan["requests"][-1]["decision"], "unsupported")

    def test_invalid_settings_fail_closed(self):
        bad = [
            {"allowed_repository_hosts": ["*.example.internal"]},
            {"allowed_repository_hosts": ["https://github.com"]},
            {"allowed_repository_hosts": ["github.com:443"]},
            {"allowed_repository_hosts": ["github.com/evil"]},
        ]
        bad += [
            {"npm_registry_url": value}
            for value in (
                None,
                "http://mirror.test",
                "https://user:secret@mirror.test/npm",
                "https://mirror.test/npm?token=secret",
                "https://mirror.test/npm#x",
                "https://mirror.test/%2e%2e",
                "https://mirror.test/npm/../other",
                "https://mirror.test/npm//other",
                "https://mirror.test:0/npm",
                "https://api.osv.dev",
                "https://mirror.test\\@evil.test",
                "https://mirror.test/npm\n",
            )
        ]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate(policy(**value))
        self.assertEqual(
            validate(policy(allowed_repository_hosts=[], npm_registry_url="https://mirror.test:8443/repository/npm/"))[
                "schema"
            ],
            "oss-gate.settings/1",
        )

    def test_registry_grant_is_limited_to_origin_prefix_and_identifiers(self):
        base = "https://mirror.test:8443/repository/npm"
        config = policy(npm_registry_url=base, deny_identifiers=["npm:@internal/*"])
        blocked = [
            base + "/%40internal%2Fsecret/1.0.0",
            "https://registry.npmjs.org/demo/1.0.0",
            "https://mirror.test:8443/repository/npm-other/demo",
            "https://mirror.test:8443/elsewhere/demo",
            base + "/demo/1.0.0/extra",
            base + "/demo?token=x",
            base + "/%2e%2e/1.0.0",
            base + "/demo/%2fsecret",
            base + "/demo/%252e",
            base + "/demo/..",
        ]
        with policy_scope(config), legacy_server.fake({}) as http:
            for url in blocked:
                with self.subTest(url=url), self.assertRaises(api.ApiError) as error:
                    api._request("GET", url)
                self.assertEqual(error.exception.extra["code"], "policy_blocked")
            self.assertEqual(http.calls, [])
        with policy_scope(policy(npm_registry_url=base, services=[])), legacy_server.fake({}) as http:
            with self.assertRaises(api.ApiError):
                api._request("GET", base + "/demo/1.0.0")
            self.assertEqual(http.calls, [])

    def test_cli_project_and_manifest_use_shared_service_and_keep_full_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "project.json"
            pid = api.DEPSDEV_BASE + "/projects/github.com%2Forg%2Frepo"
            with (
                legacy_server.fake({pid: {}, pid + ":packageversions": {"versions": []}}),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(cli.main(["project", "org/repo", "--out", str(out)]), 0)
            self.assertIn("packages", json.loads(out.read_text()))
            manifest = Path(tmp) / "requirements.txt"
            manifest.write_text("requests==2.25.1\n")
            out = Path(tmp) / "audit.json"
            with (
                legacy_server.fake({legacy_server.QB: {"results": [{"vulns": [{"id": "TEST-ID"}]}]}}),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(cli.main(["audit", str(manifest), "--type", "requirements.txt", "--out", str(out)]), 0)
            self.assertEqual(json.loads(out.read_text())["packages"][0]["vuln_ids"], ["TEST-ID"])
            old = out.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                cli.main(["audit", str(manifest), "--type", "requirements.txt", "--out", str(out)])
            self.assertEqual(out.read_bytes(), old)


class MirrorLookup(unittest.TestCase):
    # Reuse the transport fixture, without repeating the original test methods.
    routes = lookup_fixtures.LookupFailures.routes
    lookup = lookup_fixtures.LookupFailures.lookup

    def setUp(self):
        env = patch.dict(os.environ)
        env.start()
        os.environ.pop("OSS_GATE_POLICY", None)
        self.addCleanup(env.stop)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        p = Path(tmp.name) / "policy.json"
        self.base = "https://mirror.test:8443/repository/npm"
        p.write_text(json.dumps(policy(npm_registry_url=self.base)))
        os.environ["OSS_GATE_POLICY"] = str(p)
        self.pkg = legacy_server.PKG("npm", "@scope/demo")
        self.url = self.base + "/%40scope%2Fdemo/1.0.0"
        sleeper = patch.object(api.time, "sleep")
        sleeper.start()
        self.addCleanup(sleeper.stop)

    def test_mirror_existence_is_not_review_evidence(self):
        with self.routes(
            {
                self.pkg: httpx.Response(404),
                self.url: httpx.Response(200, json={"name": "@scope/demo", "version": "1.0.0"}),
            }
        ) as calls:
            result = self.lookup("npm", "@scope/demo", "1.0.0")
        self.assertEqual(result["code"], "depsdev_metadata_unavailable")
        self.assertEqual(result["registry_check"]["source_kind"], "configured_mirror")
        self.assertNotIn("verdict", result)
        self.assertNotIn("public registry confirms", result["hint"])
        self.assertEqual(len(calls), 2)

    def test_scoped_package_and_encoded_build_metadata_version(self):
        version = "1.0.0+build.1"
        url = self.base + "/%40scope%2Fdemo/1.0.0%2Bbuild.1"
        with self.routes(
            {self.pkg: httpx.Response(404), url: httpx.Response(200, json={"name": "@scope/demo", "version": version})}
        ):
            result = self.lookup("npm", "@scope/demo", version)
        self.assertEqual(result["registry_check"]["status"], "found")

    def test_mirror_absence_is_scoped_to_selected_mirror(self):
        for status, expected in ((404, "mirror_package_not_found"), (200, "mirror_version_not_found")):
            with self.routes(
                {
                    self.pkg: httpx.Response(404),
                    self.url: httpx.Response(404),
                    self.base + "/%40scope%2Fdemo": httpx.Response(status, json={"name": "@scope/demo"}),
                }
            ) as calls:
                result = self.lookup("npm", "@scope/demo", "1.0.0")
            self.assertEqual(result["code"], expected)
            self.assertTrue(all("registry.npmjs.org" not in url for _, url, _ in calls))

    def test_mirror_failure_never_falls_back_to_public_registry(self):
        for response in (
            httpx.Response(401),
            httpx.Response(403),
            httpx.Response(302, headers={"Location": "https://registry.npmjs.org/@scope/demo"}),
            httpx.Response(503),
            httpx.Response(200, text="bad JSON"),
            httpx.Response(200, json={"name": "other", "version": "1.0.0"}),
            httpx.ReadTimeout("test"),
        ):
            with (
                self.subTest(response=response),
                self.routes({self.pkg: httpx.Response(404), self.url: response}) as calls,
            ):
                result = self.lookup("npm", "@scope/demo", "1.0.0")
            self.assertEqual(result["code"], "lookup_unresolved")
            self.assertEqual(result["registry_check"]["status"], "unverified")
            self.assertTrue(all(url in (self.pkg, self.url) for _, url, _ in calls))
            if isinstance(response, httpx.Response) and response.status_code in (401, 403):
                self.assertEqual(result["registry_check"]["checks"][0]["code"], "registry_access_denied")

    def test_depsdev_unavailable_does_not_become_mirror_analysis(self):
        with self.routes({self.pkg: httpx.Response(503)}) as calls:
            result = self.lookup("npm", "@scope/demo", "1.0.0")
        self.assertEqual(result["code"], "upstream_lookup_failed")
        self.assertNotIn("registry_check", result)
        self.assertTrue(all(url == self.pkg for _, url, _ in calls))
