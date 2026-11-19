"""Keep absence, upstream failure and insufficient review evidence distinct."""

import json
import logging
import sys
import tempfile
import unittest
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/oss-gate/mcp/depsdev"))
import server
from collect import collect

PKG = f"{server.DEPSDEV_BASE}/systems/pypi/packages/demo"
VER = f"{PKG}/versions/1.0.0"
REGISTRY = "https://pypi.org/pypi/demo/json"
RELEASE = "https://pypi.org/pypi/demo/1.0.0/json"


class LookupFailures(unittest.TestCase):
    def setUp(self):
        sleeper = patch.object(server.time, "sleep")
        self.sleep = sleeper.start()
        self.addCleanup(sleeper.stop)
        quiet = patch.object(logging.getLogger("httpx"), "disabled", True)
        quiet.start()
        self.addCleanup(quiet.stop)

    @contextmanager
    def routes(self, responses):
        calls = []

        def handler(request):
            url = str(request.url)
            calls.append((request.method, url, request.content))
            self.assertIn(url, responses, "Unexpected endpoint")
            response = responses[url]
            if callable(response):
                response = response()
            if isinstance(response, Exception):
                raise response
            return response

        with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
            with patch.object(server, "_client", client):
                yield calls

    def lookup(self, system="pypi", name="demo", version="1.0.0"):
        return json.loads(server.lookup_package(system, name, version))

    def test_existing_registry_target_is_not_approved_or_saved(self):
        routes = {
            PKG: httpx.Response(404),
            RELEASE: httpx.Response(200, json={"info": {"name": "demo", "version": "1.0.0"}}),
        }
        with self.routes(routes) as calls, tempfile.TemporaryDirectory() as temp:
            result = collect(server, "pypi", "demo", "1.0.0", output_root=temp)
            self.assertEqual(result["code"], "depsdev_metadata_unavailable")
            self.assertEqual(result["registry_check"]["status"], "found")
            self.assertEqual(result["status"], 404)
            self.assertNotIn("verdict", result)
            self.assertFalse(list(Path(temp).iterdir()))
            self.assertEqual(len(calls), 2)

    def test_version_absence_is_distinct_from_package_absence(self):
        for package_status, code in [(200, "version_not_found"), (404, "package_not_found")]:
            with (
                self.subTest(package_status=package_status),
                self.routes(
                    {
                        PKG: httpx.Response(200, json={"versions": []}),
                        VER: httpx.Response(404),
                        RELEASE: httpx.Response(404),
                        REGISTRY: httpx.Response(package_status, json={"info": {"name": "demo"}}),
                    }
                ) as calls,
            ):
                result = self.lookup()
                self.assertEqual(result["code"], code)
                self.assertEqual(result["lookup_stage"], "version")
                self.assertEqual(len(calls), 4)
                self.sleep.assert_not_called()

    def test_unverified_registry_response_never_means_absent(self):
        cases = [
            httpx.Response(401),
            httpx.Response(403),
            httpx.Response(429, headers={"Retry-After": "60"}),
            httpx.Response(503),
            httpx.Response(302, headers={"Location": "https://other.example/"}),
            httpx.Response(200, text="not JSON"),
            httpx.Response(200, json=[]),
            httpx.Response(200, json={"info": {"name": "different", "version": "1.0.0"}}),
            httpx.Response(200, json={"info": {"name": "demo", "version": "2.0.0"}}),
            httpx.ReadTimeout("simulated"),
        ]
        for response in cases:
            with self.subTest(response=response), self.routes({PKG: httpx.Response(404), RELEASE: response}):
                result = self.lookup()
                self.assertEqual(result["code"], "lookup_unresolved")
                self.assertEqual(result["registry_check"]["status"], "unverified")

    def test_missing_version_with_unverified_package_stays_unknown(self):
        with self.routes({PKG: httpx.Response(404), RELEASE: httpx.Response(404), REGISTRY: httpx.Response(403)}):
            self.assertEqual(self.lookup()["code"], "lookup_unresolved")

    def test_unchecked_ecosystem_does_not_claim_nonexistence(self):
        url = f"{server.DEPSDEV_BASE}/systems/go/packages/example.com%2Fdemo"
        with self.routes({url: httpx.Response(404)}) as calls:
            result = self.lookup("go", "example.com/demo")
            self.assertEqual(result["code"], "lookup_unresolved")
            self.assertEqual(result["registry_check"]["status"], "unsupported")
            self.assertEqual(len(calls), 1)

    def test_scoped_npm_and_normalized_pypi_names(self):
        for system, name, url, payload in [
            (
                "npm",
                "@scope/demo",
                "https://registry.npmjs.org/%40scope%2Fdemo/1.0.0",
                {"name": "@scope/demo", "version": "1.0.0"},
            ),
            (
                "pypi",
                "Demo_Pkg",
                "https://pypi.org/pypi/Demo_Pkg/1.0.0/json",
                {"info": {"name": "demo-pkg", "version": "1.0.0"}},
            ),
        ]:
            from urllib.parse import quote

            missing = f"{server.DEPSDEV_BASE}/systems/{system}/packages/{quote(name, safe='')}"
            with (
                self.subTest(system=system),
                self.routes({missing: httpx.Response(404), url: httpx.Response(200, json=payload)}),
            ):
                self.assertEqual(self.lookup(system, name)["registry_check"]["status"], "found")

    def test_no_version_checks_only_package_identity(self):
        with self.routes(
            {PKG: httpx.Response(404), REGISTRY: httpx.Response(200, json={"info": {"name": "demo"}})}
        ) as calls:
            self.assertEqual(self.lookup(version="")["code"], "depsdev_metadata_unavailable")
            self.assertEqual(len(calls), 2)

    def test_normal_success_has_no_registry_requests(self):
        with self.routes(
            {
                PKG: httpx.Response(200, json={"versions": []}),
                VER: httpx.Response(
                    200, json={"versionKey": {"name": "demo", "version": "1.0.0"}, "licenses": ["MIT"]}
                ),
            }
        ) as calls:
            self.assertNotIn("error", self.lookup())
            self.assertEqual([c[1] for c in calls], [PKG, VER])

    def test_non_404_lookup_errors_do_not_probe_registries(self):
        for response, code, attempts in [
            (httpx.Response(429, headers={"Retry-After": "60"}), "upstream_rate_limited", 1),
            (httpx.Response(503), "upstream_lookup_failed", 2),
            (httpx.ReadTimeout("simulated"), "upstream_timeout", 2),
            (httpx.ConnectError("simulated"), "upstream_network_error", 2),
            (httpx.Response(200, text="broken"), "upstream_lookup_failed", 1),
        ]:
            with self.subTest(code=code), self.routes({PKG: response}) as calls:
                result = self.lookup()
                self.assertEqual(result["code"], code)
                self.assertIn("hint", result)
                self.assertNotIn("registry_check", result)
                self.assertEqual(len(calls), attempts)

    def test_invalid_version_and_unresolved_default_do_not_probe(self):
        with self.routes({}) as calls:
            self.assertIn("invalid input", self.lookup(version="../private")["error"])
            self.assertFalse(calls)
        with self.routes({PKG: httpx.Response(200, json={"versions": []})}) as calls:
            self.assertEqual(self.lookup(version="")["code"], "version_unresolved")
            self.assertEqual(len(calls), 1)

    def test_redirect_json_is_not_metadata_or_a_clean_osv_result(self):
        response = httpx.Response(
            302,
            headers={"Location": "https://other.example/"},
            json={"versions": [], "results": [{}]},
        )
        with self.routes({PKG: response}) as calls:
            result = self.lookup()
            self.assertEqual(result["code"], "upstream_lookup_failed")
            self.assertEqual(result["status"], 302)
            self.assertNotIn("registry_check", result)
            self.assertEqual(len(calls), 1)
        with self.routes({f"{server.OSV_BASE}/querybatch": response}) as calls:
            results, incomplete = server._osv_batch([("PyPI", "demo", "1.0.0")])
            self.assertEqual(results, [None])
            self.assertTrue(incomplete)
            self.assertEqual(len(calls), 1)
        self.sleep.assert_not_called()

    def test_retry_recovers_reads_and_preserves_http_attempts(self):
        for method in ("GET", "POST"):
            responses = iter([httpx.Response(503), httpx.Response(200, json={"ok": True})])
            captured = []
            token = server._capture.set(captured)
            try:
                with self.subTest(method=method), self.routes({PKG: lambda: next(responses)}) as calls:
                    result = server._get(PKG) if method == "GET" else server._post(PKG, {"queries": []})
                    self.assertEqual(result, {"ok": True})
                    self.assertEqual(len(calls), 2)
                    self.assertEqual(calls[0], calls[1])
                    self.assertEqual([c["status"] for c in captured], [503, 200])
            finally:
                server._capture.reset(token)

    def test_timeout_recovery_and_permanent_errors_are_bounded(self):
        responses = iter([httpx.ReadTimeout("simulated"), httpx.Response(200, json={"ok": True})])
        with self.routes({PKG: lambda: next(responses)}) as calls:
            self.assertEqual(server._get(PKG), {"ok": True})
            self.assertEqual(len(calls), 2)
        for status in (400, 401, 403, 404):
            with self.subTest(status=status), self.routes({PKG: httpx.Response(status)}) as calls:
                with self.assertRaises(server.ApiError):
                    server._get(PKG)
                self.assertEqual(len(calls), 1)

    def test_retry_after_short_long_date_and_invalid(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for value, expected in [("2", 2), ("60", None), ("Thu, 01 Jan 2026 00:00:01 GMT", 1), ("invalid", 0.25)]:
            with self.subTest(value=value), patch.object(server, "datetime") as clock:
                clock.now.return_value = now
                self.assertEqual(server._retry_delay(httpx.Response(429, headers={"Retry-After": value})), expected)
        with self.routes({PKG: httpx.Response(429, headers={"Retry-After": "60"})}) as calls:
            with self.assertRaises(server.ApiError):
                server._get(PKG)
            self.assertEqual(len(calls), 1)
            self.sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
