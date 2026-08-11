from __future__ import annotations

import asyncio
import socket

import httpx
import pytest

from app.crawler.exceptions import (
    CrawlerBodyTooLargeError,
    CrawlerHTTPStatusError,
    CrawlerRedirectError,
    CrawlerUnsafeHostError,
)
from app.crawler.http_client import (
    SafeAsyncCrawlerClient,
    SafeAsyncNetworkBackend,
    _resolve_safe_host,
)


async def test_resolver_rejects_mixed_public_and_private_addresses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loop = asyncio.get_running_loop()

    async def resolve(*args: object, **kwargs: object) -> list[tuple[object, ...]]:
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 443)),
        ]

    monkeypatch.setattr(loop, "getaddrinfo", resolve)
    with pytest.raises(CrawlerUnsafeHostError):
        await _resolve_safe_host("mixed.test", 443)


async def test_network_backend_connects_to_validated_ip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    async def safe(host: str, port: int) -> str:
        assert host == "example.com"
        return "93.184.216.34"

    class Backend:
        async def connect_tcp(self, host: str, port: int, **kwargs: object) -> object:
            calls.append(host)
            return object()

    monkeypatch.setattr("app.crawler.http_client._resolve_safe_host", safe)
    backend = SafeAsyncNetworkBackend(Backend())  # type: ignore[arg-type]
    await backend.connect_tcp("example.com", 443)
    assert calls == ["93.184.216.34"]


async def test_client_rejects_cross_host_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    async def safe(*args: object, **kwargs: object) -> str:
        return "93.184.216.34"

    monkeypatch.setattr("app.crawler.http_client._resolve_safe_host", safe)
    transport = httpx.MockTransport(
        lambda request: httpx.Response(302, headers={"location": "https://other.test/"})
    )
    async with SafeAsyncCrawlerClient(transport=transport) as client:
        with pytest.raises(CrawlerRedirectError):
            await client.fetch("https://example.com/")


async def test_client_enforces_body_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    async def safe(*args: object, **kwargs: object) -> str:
        return "93.184.216.34"

    monkeypatch.setattr("app.crawler.http_client._resolve_safe_host", safe)
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=b"large"))
    async with SafeAsyncCrawlerClient(transport=transport, max_bytes=4) as client:
        with pytest.raises(CrawlerBodyTooLargeError):
            await client.fetch("https://example.com/")


async def test_http_error_exposes_retry_classification(monkeypatch: pytest.MonkeyPatch) -> None:
    async def safe(*args: object, **kwargs: object) -> str:
        return "93.184.216.34"

    monkeypatch.setattr("app.crawler.http_client._resolve_safe_host", safe)
    transport = httpx.MockTransport(lambda request: httpx.Response(429))
    async with SafeAsyncCrawlerClient(transport=transport) as client:
        with pytest.raises(CrawlerHTTPStatusError) as raised:
            await client.fetch("https://example.com/")
    assert raised.value.retryable
