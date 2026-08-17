from __future__ import annotations

from types import SimpleNamespace

import httpx

from app.crawler.handlers.http_snapshot import MAX_STORED_TEXT_BYTES, http_snapshot_handler
from app.crawler.network.http_client import CrawlerResponse


class FakeClient:
    def __init__(self, response: CrawlerResponse) -> None:
        self.response = response

    async def fetch(self, url: str, *, raise_for_status: bool) -> CrawlerResponse:
        assert url == "https://example.com/data"
        assert not raise_for_status
        return self.response


async def test_snapshot_stores_capped_text_and_hash() -> None:
    content = b"a" * (MAX_STORED_TEXT_BYTES + 1)
    result = await http_snapshot_handler(
        SimpleNamespace(target_url="https://example.com/data"),  # type: ignore[arg-type]
        FakeClient(
            CrawlerResponse(
                url="https://example.com/final",
                status_code=404,
                headers=httpx.Headers({"content-type": "text/plain; charset=utf-8"}),
                content=content,
            )
        ),  # type: ignore[arg-type]
    )

    assert result["status_code"] == 404
    assert result["content_length"] == len(content)
    assert result["truncated"] is True
    assert len(str(result["body"])) == MAX_STORED_TEXT_BYTES
    assert len(str(result["sha256"])) == 64


async def test_snapshot_omits_binary_body() -> None:
    result = await http_snapshot_handler(
        SimpleNamespace(target_url="https://example.com/data"),  # type: ignore[arg-type]
        FakeClient(
            CrawlerResponse(
                url="https://example.com/data",
                status_code=200,
                headers=httpx.Headers({"content-type": "image/png"}),
                content=b"png",
            )
        ),  # type: ignore[arg-type]
    )
    assert result["body"] is None
    assert result["truncated"] is False
