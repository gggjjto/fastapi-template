"""Hatchet Cloud worker entry point.

Start locally with ``uv run python -m app.worker``.
"""

from __future__ import annotations

from hatchet_sdk import Hatchet
from hatchet_sdk.worker.worker import Worker

from app.crawler.runtime.registry import discover_handlers
from app.crawler.runtime.runner import create_crawl_task

hatchet = Hatchet()

crawl_task = create_crawl_task(hatchet)


def create_worker() -> Worker:
    discover_handlers()
    return hatchet.worker(
        "rapid-template-worker",
        slots=10,
        workflows=[crawl_task],
    )


def main() -> None:
    create_worker().start()


if __name__ == "__main__":
    main()
