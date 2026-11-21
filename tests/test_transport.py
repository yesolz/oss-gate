"""Exercise limits on actual HTTPX streams, including incomplete-evidence behavior."""

import asyncio
import json
import unittest
from unittest.mock import patch

import httpx
import legacy_server  # Sets the plugin import path.
from core import api, deepwiki
from core.transport import BoundedTransport, BoundedAsyncTransport, ResponseLimitError


class Chunks(httpx.SyncByteStream):
    def __init__(self, chunks):
        self.chunks, self.closed, self.read = chunks, False, 0

    def __iter__(self):
        for chunk in self.chunks:
            self.read += 1
            yield chunk

    def close(self):
        self.closed = True


class AsyncChunks(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks, self.closed = chunks, False

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk

    async def aclose(self):
        self.closed = True


class ResponseLimits(unittest.TestCase):
    def client(self, stream, headers=None, status=200):
        def handler(request):
            self.assertEqual(request.headers["accept-encoding"], "identity")
            return httpx.Response(status, headers=headers, stream=stream)

        return httpx.Client(transport=BoundedTransport(httpx.MockTransport(handler), limit=8))

    def test_small_response_and_exact_limit_succeed(self):
        stream = Chunks([b'{"a":', b" 1}"])
        with self.client(stream) as client:
            self.assertEqual(client.get("https://example.com").json(), {"a": 1})
        self.assertTrue(stream.closed)

    def test_missing_or_false_length_does_not_bypass_cap_and_closes_stream(self):
        for headers in ({}, {"content-length": "1"}, {"content-length": "invalid"}):
            stream = Chunks([b"12345678", b"9", b"never read"])
            with self.subTest(headers=headers), self.client(stream, headers) as client:
                with self.assertRaises(ResponseLimitError):
                    client.get("https://example.com")
                self.assertEqual(stream.read, 2)
                self.assertTrue(stream.closed)

    def test_declared_oversize_and_compressed_bodies_rejected_before_read(self):
        for headers in ({"content-length": "9"}, {"content-encoding": "gzip"}, {"content-encoding": "br"}):
            stream = Chunks([b"never read"])
            with self.subTest(headers=headers), self.client(stream, headers) as client:
                with self.assertRaises(ResponseLimitError):
                    client.get("https://example.com")
                self.assertEqual(stream.read, 0)
                self.assertTrue(stream.closed)

    def test_elapsed_time_limit_closes_stream(self):
        stream = Chunks([b"{}"])
        with self.client(stream) as client, patch("core.transport.time.monotonic", side_effect=[0, 121]):
            with self.assertRaises(ResponseLimitError):
                client.get("https://example.com")
        self.assertTrue(stream.closed)

    def test_limit_is_not_retried_or_reported_as_absence_or_zero_vulnerabilities(self):
        stream = Chunks([b"123456789"])
        with (
            self.client(stream) as client,
            patch.object(api, "_client", client),
            patch.object(api.time, "sleep") as sleep,
        ):
            result = json.loads(api._run(api._lookup_package, "pypi", "demo", "1"))
            self.assertEqual(result["code"], "upstream_response_limit")
            self.assertNotIn("registry_check", result)
            sleep.assert_not_called()
        with self.client(Chunks([b"123456789"]), status=503) as client, patch.object(api, "_client", client):
            values, incomplete = api._osv_batch([("PyPI", "demo", "1")])
            self.assertEqual(values, [None])
            self.assertTrue(incomplete)

    def test_async_limit_and_rejected_headers_close_stream(self):
        async def run(headers, chunks, succeeds):
            stream = AsyncChunks(chunks)

            async def handler(request):
                self.assertEqual(request.headers["accept-encoding"], "identity")
                return httpx.Response(200, headers=headers, stream=stream)

            async with httpx.AsyncClient(
                transport=BoundedAsyncTransport(httpx.MockTransport(handler), limit=8)
            ) as client:
                if succeeds:
                    self.assertEqual((await client.get("https://example.com")).json(), {})
                else:
                    with self.assertRaises(ResponseLimitError):
                        await client.get("https://example.com")
            self.assertTrue(stream.closed)

        for headers, chunks, succeeds in [
            ({}, [b"{}"], True),
            ({}, [b"12345678", b"9"], False),
            ({"content-encoding": "gzip"}, [b"x"], False),
        ]:
            with self.subTest(headers=headers, succeeds=succeeds):
                asyncio.run(run(headers, chunks, succeeds))

    def test_deepwiki_timeout_is_upstream_failure_and_cancels_call(self):
        real_wait_for = asyncio.wait_for
        closed = []

        async def slow(*args):
            try:
                await asyncio.sleep(10)
            finally:
                closed.append(True)

        async def short_wait(awaitable, timeout):
            self.assertEqual(timeout, 120)
            return await real_wait_for(awaitable, timeout=0.01)

        with patch.object(deepwiki, "_call", slow), patch.object(deepwiki.asyncio, "wait_for", short_wait):
            result = asyncio.run(deepwiki.request("yesolz/oss-gate"))
        self.assertEqual(result["code"], "upstream_timeout")
        self.assertEqual(closed, [True])
