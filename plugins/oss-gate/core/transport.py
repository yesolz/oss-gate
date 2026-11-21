"""Bound upstream bodies before JSON/SSE parsing, including error responses."""

import time

import httpx

MAX_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_RESPONSE_SECONDS = 120


class ResponseLimitError(httpx.HTTPError):
    """Incomplete evidence: an upstream response exceeded a resource limit."""


class Budget:
    def __init__(self, headers, limit):
        # Avoid decompression bombs: request identity and reject servers that ignore it.
        if headers.get("content-encoding", "identity").strip().lower() != "identity":
            raise ResponseLimitError("unexpected compressed upstream response")
        length = headers.get("content-length", "")
        if length.isdecimal():
            length = length.lstrip("0") or "0"
            if len(length) > len(str(limit)) or int(length) > limit:
                raise ResponseLimitError("upstream response exceeds byte limit")
        self.remaining = limit
        self.deadline = time.monotonic() + MAX_RESPONSE_SECONDS

    def consume(self, chunk):
        self.remaining -= len(chunk)
        if self.remaining < 0:
            raise ResponseLimitError("upstream response exceeds byte limit")
        if time.monotonic() > self.deadline:
            raise ResponseLimitError("upstream response exceeds time limit")


class BoundedStream(httpx.SyncByteStream):
    def __init__(self, stream, budget):
        self.stream, self.budget = stream, budget

    def __iter__(self):
        for chunk in self.stream:
            self.budget.consume(chunk)
            yield chunk

    def close(self):
        self.stream.close()


class BoundedAsyncStream(httpx.AsyncByteStream):
    def __init__(self, stream, budget):
        self.stream, self.budget = stream, budget

    async def __aiter__(self):
        async for chunk in self.stream:
            self.budget.consume(chunk)
            yield chunk

    async def aclose(self):
        await self.stream.aclose()


class BoundedTransport(httpx.BaseTransport):
    def __init__(self, transport=None, limit=MAX_RESPONSE_BYTES, *, verify=True):
        self.transport = transport if transport is not None else httpx.HTTPTransport(verify=verify, trust_env=False)
        self.limit = limit

    def handle_request(self, request):
        request.headers["accept-encoding"] = "identity"
        response = self.transport.handle_request(request)
        try:
            budget = Budget(response.headers, self.limit)
        except ResponseLimitError:
            response.close()
            raise
        response.stream = BoundedStream(response.stream, budget)
        return response

    def close(self):
        self.transport.close()


class BoundedAsyncTransport(httpx.AsyncBaseTransport):
    def __init__(self, transport=None, limit=MAX_RESPONSE_BYTES, *, verify=True):
        self.transport = (
            transport if transport is not None else httpx.AsyncHTTPTransport(verify=verify, trust_env=False)
        )
        self.limit = limit

    async def handle_async_request(self, request):
        request.headers["accept-encoding"] = "identity"
        response = await self.transport.handle_async_request(request)
        try:
            budget = Budget(response.headers, self.limit)
        except ResponseLimitError:
            await response.aclose()
            raise
        response.stream = BoundedAsyncStream(response.stream, budget)
        return response

    async def aclose(self):
        await self.transport.aclose()
