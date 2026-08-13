from __future__ import annotations

import asyncio
import time
from typing import Any, Protocol

import structlog
from hatchet_sdk import Hatchet
from hatchet_sdk.exceptions import IdempotencyCollisionError

from app.core.config import get_settings
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
    start = time.perf_counter()
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
        terminal = await repository.record_dispatch_failure(
            job_id=job.id, tenant_id=job.tenant_id, error=str(exc)
        )
        await repository.session.commit()
        (logger.error if terminal else logger.warning)(
            "crawler.job.failed" if terminal else "crawler.job.retrying",
            crawl_job_id=str(job.id),
            handler_name=job.handler_name,
            target_host=job.target_host,
            dispatch_attempt=job.dispatch_attempts,
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
            error_category="transient",
            error_code="DISPATCH_FAILED",
        )
        return False

    if not run_id:
        terminal = await repository.record_dispatch_failure(
            job_id=job.id,
            tenant_id=job.tenant_id,
            error="Hatchet returned an empty run id",
        )
        await repository.session.commit()
        (logger.error if terminal else logger.warning)(
            "crawler.job.failed" if terminal else "crawler.job.retrying",
            crawl_job_id=str(job.id),
            handler_name=job.handler_name,
            target_host=job.target_host,
            dispatch_attempt=job.dispatch_attempts,
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
            error_category="transient",
            error_code="DISPATCH_FAILED",
        )
        return False

    marked = await repository.mark_dispatched(
        job_id=job.id,
        tenant_id=job.tenant_id,
        hatchet_run_id=run_id,
    )
    await repository.session.commit()
    if marked:
        logger.info(
            "crawler.job.dispatched",
            crawl_job_id=str(job.id),
            hatchet_run_id=run_id,
            handler_name=job.handler_name,
            target_host=job.target_host,
            dispatch_attempt=job.dispatch_attempts,
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )
    else:
        logger.error(
            "crawler.job.failed",
            crawl_job_id=str(job.id),
            hatchet_run_id=run_id,
            handler_name=job.handler_name,
            target_host=job.target_host,
            dispatch_attempt=job.dispatch_attempts,
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
            error_category="permanent",
            error_code="HATCHET_RUN_ID_CONFLICT",
        )
    return marked


async def run_dispatcher() -> None:
    settings = get_settings()
    hatchet = Hatchet()
    task = create_crawl_task(hatchet)
    while True:
        try:
            async with AsyncSessionLocal() as session:
                dispatched = await dispatch_once(repository=CrawlerRepository(session), task=task)
        except Exception:
            logger.exception("crawler.dispatcher.batch_failed")
            await asyncio.sleep(settings.crawler_dispatch_interval_seconds)
            continue

        if dispatched:
            logger.info("crawler.dispatcher.batch", dispatched=dispatched)
            continue
        await asyncio.sleep(settings.crawler_dispatch_interval_seconds)


def main() -> None:
    asyncio.run(run_dispatcher())


if __name__ == "__main__":
    main()
