"""Verify additional trust with real local TLS, without installing test CAs globally."""

import asyncio
from contextlib import contextmanager
from contextvars import copy_context
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import ssl
import sys
import tempfile
import threading
import unittest
from unittest.mock import AsyncMock, patch

import certifi
import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/oss-gate"))
from core import api, deepwiki
from core.policy import evaluate
from core.service import invoke
from core.settings import policy_scope, validate
from core.tls import build_context, TLSConfigurationError, EVIDENCE
from core.render import render
from core.snapshot import verify
from test_review import clean


def policy(path=None, **network):
    if path is not None:
        network["additional_ca_file"] = str(path)
    return {"schema": "oss-gate.settings/1", "name": "Test trust", "version": "1", "network": network}


def issue(subject, public_key, issuer, issuer_key, *, ca=False, expired=False):
    now = datetime.now(timezone.utc)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=2))
        .not_valid_after(now + timedelta(days=-1 if expired else 2))
        .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=not ca,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=ca,
                crl_sign=ca,
                encipher_only=None,
                decipher_only=None,
            ),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(public_key), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(issuer_key.public_key()), critical=False)
    )
    if not ca:
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False
        ).add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
    return builder.sign(issuer_key, hashes.SHA256())


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b'{"ok":true}'
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class AdditionalTrust(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="oss-gate-test-ca-")
        cls.root = Path(cls.tmp.name)
        cls.ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Ephemeral OSS Gate test CA")])
        cert = issue(cls.subject, cls.ca_key.public_key(), cls.subject, cls.ca_key, ca=True)
        cls.ca = cls.root / "test ca.pem"
        cls.ca.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.key = cls.root / "server.key"
        cls.key.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
            )
        )
        cls.certs = {}
        for expired in (False, True):
            cert = issue(
                x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]),
                key.public_key(),
                cls.subject,
                cls.ca_key,
                expired=expired,
            )
            path = cls.root / ("expired.pem" if expired else "server.pem")
            path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
            cls.certs[expired] = path

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        env = patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("OSS_GATE_POLICY", None)

    @contextmanager
    def server(self, expired=False):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(self.certs[expired], self.key)
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        try:
            yield f"https://localhost:{server.server_port}"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_default_is_unchanged_and_custom_ca_is_additive(self):
        self.assertEqual(build_context(None), (True, None))
        ctx, evidence = build_context(policy(self.ca))
        baseline = ssl.create_default_context(cafile=certifi.where())
        self.assertTrue(set(baseline.get_ca_certs(binary_form=True)) <= set(ctx.get_ca_certs(binary_form=True)))
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(ctx.check_hostname)
        self.assertEqual(evidence["additional_ca_sha256"], hashlib.sha256(self.ca.read_bytes()).hexdigest())

    def test_sync_tls_requires_selected_ca_and_keeps_hostname_and_expiry_checks(self):
        with self.server() as url:
            config = policy(self.ca, npm_registry_url=url)
            with policy_scope(config), api.client_scope(config):
                self.assertTrue(api._request("GET", url + "/demo/1").json()["ok"])
                with self.assertRaises(httpx.ConnectError):
                    api._active_client.get().get(url.replace("localhost", "127.0.0.1") + "/demo/1")
            # A subsequent operation must not inherit the previous connection pool or CA.
            with policy_scope(policy(npm_registry_url=url)), api.client_scope(None), patch.object(api.time, "sleep"):
                with self.assertRaises(httpx.ConnectError):
                    api._request("GET", url + "/demo/1")
            self.assertIsNone(api._active_client.get())
            self.assertIsNone(EVIDENCE.get())
        ctx, _ = build_context(policy(self.ca))
        with self.server(expired=True) as url, httpx.Client(verify=ctx, trust_env=False) as client:
            with self.assertRaises(httpx.ConnectError):
                client.get(url)

    def test_async_deepwiki_factory_uses_same_trust(self):
        async def request(url, verify):
            async with deepwiki.client_factory(verify=verify) as client:
                return (await client.get(url)).json()

        ctx, _ = build_context(policy(self.ca))
        with self.server() as url:
            self.assertTrue(asyncio.run(request(url, ctx))["ok"])
            for target, verify in ((url, True), (url.replace("localhost", "127.0.0.1"), ctx)):
                with self.assertRaises(httpx.ConnectError):
                    asyncio.run(request(target, verify))
        with self.server(expired=True) as url, self.assertRaises(httpx.ConnectError):
            asyncio.run(request(url, ctx))

    def test_workers_inherit_client_without_leaking_between_parallel_operations(self):
        with self.server() as url:

            def operation(custom):
                config = policy(self.ca if custom else None, npm_registry_url=url)
                with policy_scope(config), api.client_scope(config), ThreadPoolExecutor(max_workers=1) as pool:
                    return pool.submit(copy_context().run, api._request, "GET", url + "/demo/1").result().json()

            with ThreadPoolExecutor(max_workers=2) as pool, patch.object(api.time, "sleep"):
                yes, no = pool.submit(operation, True), pool.submit(operation, False)
                self.assertTrue(yes.result()["ok"])
                with self.assertRaises(httpx.ConnectError):
                    no.result()

    def test_bad_ca_stops_both_entry_points_before_network_and_has_safe_errors(self):
        for body in (b"", b"not a certificate", self.ca.read_bytes() + self.key.read_bytes(), b"x" * (1024 * 1024 + 1)):
            with self.subTest(length=len(body)), tempfile.TemporaryDirectory() as tmp:
                ca = Path(tmp) / "sensitive-path.pem"
                ca.write_bytes(body)
                p = Path(tmp) / "policy.json"
                p.write_text(json.dumps(policy(ca)))
                with patch.object(api._client, "get") as get, patch.object(deepwiki, "_call") as connect:
                    results = [
                        json.loads(invoke("lookup_package", "pypi", "demo", "1", policy_path=str(p))),
                        asyncio.run(deepwiki.request("owner/repo", policy_path=str(p))),
                    ]
                for result in results:
                    self.assertEqual(result["code"], "tls_configuration_invalid")
                    self.assertNotIn("sensitive-path", json.dumps(result))
                get.assert_not_called()
                connect.assert_not_called()
        for path in (self.root / "missing.pem", self.root):
            with self.assertRaises(TLSConfigurationError):
                build_context(policy(path))

    def test_policy_schema_forbids_insecure_or_ambient_options(self):
        for value in (
            "relative.pem",
            "~/ca.pem",
            "",
            False,
            None,
            "https://example.org/ca.pem",
            "//host/share/ca.pem",
            "C:relative.pem",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate(policy(**{"additional_ca_file": value}))
        for key, value in (("verify", False), ("trust_env", True), ("use_system_store", True)):
            with self.assertRaises(ValueError):
                validate(policy(**{key: value}))
        # Saved policy is structurally readable on another OS and without the CA file.
        for path in ("/etc/company/ca.pem", "C:\\Company\\ca.pem"):
            validate(policy(path))

    def test_selected_policy_wires_service_and_deepwiki_contexts(self):
        with self.server() as url, tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "policy.json"
            config = policy(self.ca, npm_registry_url=url)
            p.write_text(json.dumps(config))

            def lookup(*args):
                return api._request("GET", url + "/demo/1").json()

            with patch.object(api, "_lookup_package", lookup):
                result = json.loads(invoke("lookup_package", "npm", "demo", "1", policy_path=str(p)))
            self.assertTrue(result["ok"])
            with patch.object(deepwiki, "_call", AsyncMock(return_value={"content": []})) as call:
                result = asyncio.run(deepwiki.request("owner/repo", policy_path=str(p)))
            self.assertIsInstance(call.call_args.args[-1], ssl.SSLContext)
            self.assertIn("additional_ca_sha256", result["tls_trust"])
            # Trust is not an egress grant.
            config["network"]["services"] = []
            p.write_text(json.dumps(config))
            with patch.object(api, "_lookup_package", lookup), patch.object(deepwiki, "_call") as call:
                self.assertEqual(
                    json.loads(invoke("lookup_package", "npm", "demo", "1", policy_path=str(p)))["code"],
                    "policy_blocked",
                )
                self.assertEqual(
                    asyncio.run(deepwiki.request("owner/repo", policy_path=str(p)))["code"], "policy_blocked"
                )
                call.assert_not_called()

    def test_plan_and_saved_policy_evaluation_do_not_load_ca_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "policy.json"
            config = policy(Path(tmp) / "missing.pem")
            p.write_text(json.dumps(config))
            result = json.loads(invoke("plan", "pypi", "demo", "1", policy_path=str(p)))
            self.assertFalse(result["network_performed"])
            from test_extensions import with_policy

            self.assertEqual(evaluate(with_policy(clean(), config))["overall"], "allow")

    def test_collection_seals_actual_ca_hash_and_renders_without_original_ca(self):
        with tempfile.TemporaryDirectory() as tmp:
            ca = Path(tmp) / "ca.pem"
            ca.write_bytes(self.ca.read_bytes())
            p = Path(tmp) / "policy.json"
            p.write_text(json.dumps(policy(ca)))
            fixture = clean()
            with (
                patch.object(api, "_lookup_package", return_value=fixture["lookup_package"]),
                patch.object(api, "_get_dependencies", return_value=fixture["get_dependencies"]),
                patch.object(api, "_osv_batch", return_value=([[]], False)),
            ):
                result = json.loads(
                    invoke("collect_review", "npm", "demo", "1.0.0", output_root=tmp, policy_path=str(p))
                )
            data = json.loads(Path(result["data"]).read_text())
            self.assertEqual(data["tls_trust"]["additional_ca_sha256"], hashlib.sha256(ca.read_bytes()).hexdigest())
            self.assertEqual(result["tls_trust"], data["tls_trust"])
            ca.unlink()
            verify(result["folder"])
            for lang in ("ko", "en"):
                self.assertIn(f'lang="{lang}"', render(data, "Review", lang))

    def test_environment_ca_and_proxy_variables_do_not_override_explicit_trust(self):
        with (
            self.server() as url,
            patch.dict(
                os.environ,
                {
                    "SSL_CERT_FILE": str(self.root / "missing.pem"),
                    "SSL_CERT_DIR": str(self.root / "missing"),
                    "HTTPS_PROXY": "http://127.0.0.1:1",
                    "ALL_PROXY": "http://127.0.0.1:1",
                },
            ),
        ):
            config = policy(self.ca, npm_registry_url=url)
            with policy_scope(config), api.client_scope(config):
                self.assertTrue(api._request("GET", url + "/demo/1").json()["ok"])

            async def check():
                ctx, _ = build_context(config)
                async with deepwiki.client_factory(verify=ctx) as client:
                    self.assertTrue((await client.get(url)).json()["ok"])

            asyncio.run(check())
