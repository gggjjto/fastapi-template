from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog

from app.crawler.application.service import _next_cron_time
from app.crawler.persistence.repository import CrawlerRepository
from app.db.session import AsyncSessionLocal

logger = structlog.get_logger(__name__)
SCHEDULER_INTERVAL_SECONDS = 30.0


async def schedule_once(*, repository: CrawlerRepository, batch_size: int = 100) -> int:
    now = datetime.now(UTC)
    targets = await repository.lease_due_targets(now=now, limit=batch_size)
    for target in targets:
        if target.next_run_at is None:
            raise RuntimeError("leased crawl target has no next_run_at")
        scheduled_for = target.next_run_at.astimezone(UTC)
        await repository.create_job(
            tenant_id=target.tenant_id,
            crawl_target_id=target.id,
            idempotency_key=f"schedule:{target.id}:{scheduled_for.isoformat()}",
            scheduled_for=scheduled_for,
        )
        target.next_run_at = _next_cron_time(
            target.schedule_cron,
            target.schedule_timezone,
            after=now,
        )
    await repository.session.commit()
    return len(targets)


async def run_scheduler() -> None:
    while True:
        try:
            async with AsyncSessionLocal() as session:
                scheduled = await schedule_once(repository=CrawlerRepository(session))
        except Exception:
            logger.exception("crawler.scheduler.batch_failed")
        else:
            if scheduled:
                logger.info("crawler.scheduler.batch", scheduled=scheduled)
                continue
        await asyncio.sleep(SCHEDULER_INTERVAL_SECONDS)


def main() -> None:
    asyncio.run(run_scheduler())


if __name__ == "__main__":
    main()
