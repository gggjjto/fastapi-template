from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Awaitable, Callable

from app.crawler.exceptions import PermanentCrawlerError
from app.crawler.http_client import SafeAsyncCrawlerClient
from app.crawler.models import CrawlTarget

CrawlerHandler = Callable[[CrawlTarget, SafeAsyncCrawlerClient], Awaitable[dict[str, object]]]


class DuplicateCrawlerError(PermanentCrawlerError):
    pass


class UnknownCrawlerError(PermanentCrawlerError):
    pass


class CrawlerRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, CrawlerHandler] = {}

    def register(self, name: str, handler: CrawlerHandler) -> None:
        if name in self._handlers:
            raise DuplicateCrawlerError(f"duplicate crawler handler: {name}")
        self._handlers[name] = handler

    def get(self, name: str) -> CrawlerHandler:
        try:
            return self._handlers[name]
        except KeyError as exc:
            raise UnknownCrawlerError(f"unknown crawler handler: {name}") from exc

    def values(self) -> dict[str, CrawlerHandler]:
        return dict(self._handlers)


registry = CrawlerRegistry()


def register_handler(name: str) -> Callable[[CrawlerHandler], CrawlerHandler]:
    def decorator(handler: CrawlerHandler) -> CrawlerHandler:
        registry.register(name, handler)
        return handler

    return decorator


def discover_handlers() -> None:
    from app.crawler import handlers

    for module in pkgutil.iter_modules(handlers.__path__, f"{handlers.__name__}."):
        importlib.import_module(module.name)
