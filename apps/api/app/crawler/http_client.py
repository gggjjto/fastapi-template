from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import AsyncIterable, Iterable
from dataclasses import dataclass
from typing import Any, cast

import httpcore
import httpx
from httpcore._backends.anyio import AnyIOBackend
from httpx._config import create_ssl_context
from httpx._transports.default import AsyncResponseStream, map_httpcore_exceptions

from app.crawler import exceptions as crawler_exceptions

# httpcore's AsyncNetworkBackend contract names this parameter `timeout`.
# ruff: noqa: ASYNC109


class _FallbackCrawlerNetworkError(Exception):
    pass


class _FallbackCrawlerUnsafeHostError(_FallbackCrawlerNetworkError):
    pass


class _FallbackCrawlerRedirectError(_FallbackCrawlerNetworkError):
    pass


class _FallbackCrawlerBodyTooLargeError(_FallbackCrawlerNetworkError):
    pass


class _FallbackCrawlerHTTPStatusError(_FallbackCrawlerNetworkError):
    pass


def _exception_type(name: str, fallback: type[Exception]) -> type[Exception]:
    value = getattr(crawler_exceptions, name, fallback)
    return value if isinstance(value, type) and issubclass(value, Exception) else fallback


CrawlerNetworkError = _exception_type("CrawlerNetworkError", _FallbackCrawlerNetworkError)
CrawlerUnsafeHostError = _exception_type("CrawlerUnsafeHostError", _FallbackCrawlerUnsafeHostError)
CrawlerRedirectError = _exception_type("CrawlerRedirectError", _FallbackCrawlerRedirectError)
CrawlerBodyTooLargeError = _exception_type(
    "CrawlerBodyTooLargeError",
    _FallbackCrawlerBodyTooLargeError,
)
CrawlerHTTPStatusError = _exception_type("CrawlerHTTPStatusError", _FallbackCrawlerHTTPStatusError)


DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
DEFAULT_TOTAL_TIMEOUT = 30.0
DEFAULT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_MAX_REDIRECTS = 5
REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}


@dataclass(frozen=True, slots=True)
class CrawlerResponse:
    url: str
    status_code: int
    headers: httpx.Headers
    content: bytes


def _is_forbidden_ip(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


async def _resolve_safe_host(host: str, port: int) -> str:
    try:
        addresses = await asyncio.get_running_loop().getaddrinfo(
            host,
            port,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
        )
    except OSError as exc:
        raise CrawlerNetworkError(f"DNS resolution failed for {host!r}") from exc

    safe_ip: str | None = None
    seen: set[str] = set()
    for *_, sockaddr in addresses:
        address = sockaddr[0]
        if address in seen:
            continue
        seen.add(address)
        if _is_forbidden_ip(address):
            raise CrawlerUnsafeHostError(f"Refusing unsafe address {address!r} for {host!r}")
        if safe_ip is None:
            safe_ip = address

    if safe_ip is None:
        raise CrawlerNetworkError(f"DNS resolution returned no addresses for {host!r}")
    return safe_ip


class SafeAsyncNetworkBackend(httpcore.AsyncNetworkBackend):
    """httpcore backend that resolves and blocks unsafe targets before TCP connect."""

    def __init__(self, backend: httpcore.AsyncNetworkBackend | None = None) -> None:
        self._backend = backend or AnyIOBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        safe_ip = await _resolve_safe_host(host, port)
        return await self._backend.connect_tcp(
            safe_ip,
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        raise CrawlerUnsafeHostError("Unix sockets are not allowed for crawler requests")


class SafeAsyncHTTPTransport(httpx.AsyncBaseTransport):
    def __init__(
        self,
        *,
        verify: bool = True,
        http2: bool = False,
        limits: httpx.Limits | None = None,
        network_backend: httpcore.AsyncNetworkBackend | None = None,
    ) -> None:
        limits = limits or httpx.Limits(
            max_connections=20,
            max_keepalive_connections=0,
            keepalive_expiry=0.0,
        )
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=create_ssl_context(verify=verify, trust_env=False),
            max_connections=limits.max_connections,
            max_keepalive_connections=limits.max_keepalive_connections,
            keepalive_expiry=limits.keepalive_expiry,
            http1=True,
            http2=http2,
            network_backend=network_backend or SafeAsyncNetworkBackend(),
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        assert isinstance(request.stream, httpx.AsyncByteStream)
        req = httpcore.Request(
            method=request.method,
            url=httpcore.URL(
                scheme=request.url.raw_scheme,
                host=request.url.raw_host,
                port=request.url.port,
                target=request.url.raw_path,
            ),
            headers=request.headers.raw,
            content=request.stream,
            extensions=request.extensions,
        )
        with map_httpcore_exceptions():
            resp = await self._pool.handle_async_request(req)

        stream = cast(AsyncIterable[bytes], resp.stream)
        return httpx.Response(
            status_code=resp.status,
            headers=resp.headers,
            stream=AsyncResponseStream(stream),
            extensions=resp.extensions,
        )

    async def aclose(self) -> None:
        await self._pool.aclose()


class SafeAsyncCrawlerClient:
    def __init__(
        self,
        *,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
        total_timeout: float = DEFAULT_TOTAL_TIMEOUT,
        max_bytes: int = DEFAULT_MAX_BYTES,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._max_bytes = max_bytes
        self._max_redirects = max_redirects
        self._total_timeout = total_timeout
        self._client = httpx.AsyncClient(
            follow_redirects=False,
            timeout=timeout,
            transport=transport or SafeAsyncHTTPTransport(),
            trust_env=False,
        )

    async def __aenter__(self) -> SafeAsyncCrawlerClient:
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._client.__aexit__(*args)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def fetch(self, url: str, *, headers: httpx.Headers | None = None) -> CrawlerResponse:
        try:
            async with asyncio.timeout(self._total_timeout):
                return await self._fetch(url, headers=headers)
        except TimeoutError as exc:
            raise CrawlerNetworkError(f"Crawler request exceeded {self._total_timeout}s") from exc

    async def _fetch(self, url: str, *, headers: httpx.Headers | None = None) -> CrawlerResponse:
        next_url = httpx.URL(url)
        if next_url.scheme not in {"http", "https"}:
            raise CrawlerUnsafeHostError(f"Unsupported crawler URL scheme: {next_url.scheme!r}")

        origin_host = next_url.host
        if origin_host is None:
            raise CrawlerUnsafeHostError("Crawler URL must include a host")

        for _ in range(self._max_redirects + 1):
            port = next_url.port or (443 if next_url.scheme == "https" else 80)
            await _resolve_safe_host(origin_host, port)
            response = await self._request(next_url, headers=headers)
            if response.status_code not in REDIRECT_STATUS_CODES:
                if response.status_code >= 400:
                    raise CrawlerHTTPStatusError(response.status_code, str(next_url))
                return response

            location = response.headers.get("location")
            if not location:
                return response
            redirected_url = next_url.join(location)
            if redirected_url.host != origin_host:
                raise CrawlerRedirectError(
                    f"Cross-host redirect refused: {next_url} -> {redirected_url}"
                )
            next_url = redirected_url

        raise CrawlerRedirectError(f"Too many redirects for {url}")

    async def _request(
        self,
        url: httpx.URL,
        *,
        headers: httpx.Headers | None = None,
    ) -> CrawlerResponse:
        try:
            async with self._client.stream("GET", url, headers=headers) as response:
                content = await self._read_capped(response)
                return CrawlerResponse(
                    url=str(response.url),
                    status_code=response.status_code,
                    headers=response.headers,
                    content=content,
                )
        except (httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError) as exc:
            raise CrawlerNetworkError(f"Network request failed for {url}") from exc

    async def _read_capped(self, response: httpx.Response) -> bytes:
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > self._max_bytes:
                raise CrawlerBodyTooLargeError(f"Response body exceeds {self._max_bytes} bytes")
            chunks.append(chunk)
        return b"".join(chunks)
