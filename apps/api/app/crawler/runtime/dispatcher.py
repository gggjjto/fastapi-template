from __future__ import annotations

import asyncio
from typing import Any, Protocol

import structlog
from hatchet_sdk import Hatchet
from hatchet_sdk.exceptions import IdempotencyCollisionError

from app.crawler.domain.constants import LEASE_SECONDS
from app.crawler.domain.schemas import CrawlTaskInput
from app.crawler.persistence.repository import CrawlerRepository, LeasedCrawlJob
from app.crawler.runtime.runner import create_crawl_task
from app.db.session import AsyncSessionLocal

logger = structlog.get_logger(__name__)


class CrawlTaskDispatcher(Protocol):
    async def aio_run(self, *, input: CrawlTaskInput, wait_for_result: bool) -> Any: ...


async def dispatch_once(
    *, repository: CrawlerRepository, task: CrawlTaskDispatcher, batch_size: int = 100
) -> int:
    jobs = await repository.lease_pending_jobs(limit=batch_size, lease_seconds=LEASE_SECONDS)
    await repository.session.commit()
    dispatched = 0
    for job in jobs:
        if await _dispatch_job(repository, task, job):
            dispatched += 1
    return dispatched


async def _dispatch_job(
    repository: CrawlerRepository, task: CrawlTaskDispatcher, job: LeasedCrawlJob
) -> bool:
    task_input = CrawlTaskInput(
        crawl_job_id=job.id,
        tenant_id=job.tenant_id,
        target_url_id=job.target_url_id,
        target_host=job.target_host,
    )
    try:
        run = await task.aio_run(input=task_input, wait_for_result=False)
        run_id = str(getattr(run, "workflow_run_id", getattr(run, "run_id", run)))
    except IdempotencyCollisionError as exc:
        run_id = exc.existing_run_external_id
    except Exception as exc:
        await repository.record_dispatch_failure(
            job_id=job.id, tenant_id=job.tenant_id, error=str(exc)
        )
        await repository.session.commit()
        return False

    if not run_id:
        await repository.record_dispatch_failure(
            job_id=job.id,
            tenant_id=job.tenant_id,
            error="Hatchet returned an empty run id",
        )
        await repository.session.commit()
        return False

    marked = await repository.mark_dispatched(
        job_id=job.id,
        tenant_id=job.tenant_id,
        hatchet_run_id=run_id,
    )
    await repository.session.commit()
    return marked


async def run_dispatcher() -> int:
    hatchet = Hatchet()
    task = create_crawl_task(hatchet)
    async with AsyncSessionLocal() as session:
        return await dispatch_once(repository=CrawlerRepository(session), task=task)


def main() -> None:
    dispatched = asyncio.run(run_dispatcher())
    logger.info("crawler.dispatcher.done", dispatched=dispatched)


if __name__ == "__main__":
    main()
