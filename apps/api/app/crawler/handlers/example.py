from __future__ import annotations

from app.crawler.domain.models import CrawlTarget
from app.crawler.network.http_client import SafeAsyncCrawlerClient
from app.crawler.runtime.registry import register_handler


@register_handler("example")
async def example_handler(target: CrawlTarget, client: SafeAsyncCrawlerClient) -> dict[str, object]:
    del client
    return {"handler": "example", "target_url_id": str(target.target_url_id)}
