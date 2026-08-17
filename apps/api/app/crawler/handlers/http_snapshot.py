from __future__ import annotations

import hashlib

from app.crawler.domain.models import CrawlTarget
from app.crawler.domain.schemas import CrawlResult
from app.crawler.network.http_client import SafeAsyncCrawlerClient
from app.crawler.runtime.registry import register_handler

MAX_STORED_TEXT_BYTES = 256 * 1024
TEXT_MEDIA_TYPES = {
    "application/json",
    "application/xml",
    "application/xhtml+xml",
}


@register_handler("http_snapshot")
async def http_snapshot_handler(
    target: CrawlTarget, client: SafeAsyncCrawlerClient
) -> dict[str, object]:
    response = await client.fetch(target.target_url, raise_for_status=False)
    content_type = response.headers.get("content-type")
    media_type = content_type.split(";", 1)[0].strip().lower() if content_type else None
    body: str | None = None
    truncated = False
    if media_type and (
        media_type.startswith("text/")
        or media_type in TEXT_MEDIA_TYPES
        or media_type.endswith("+json")
        or media_type.endswith("+xml")
    ):
        stored = response.content[:MAX_STORED_TEXT_BYTES]
        truncated = len(stored) < len(response.content)
        body = stored.decode("utf-8", errors="replace")

    return CrawlResult(
        final_url=response.url,
        status_code=response.status_code,
        content_type=content_type,
        content_length=len(response.content),
        sha256=hashlib.sha256(response.content).hexdigest(),
        body=body,
        truncated=truncated,
    ).model_dump()
