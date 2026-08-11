from __future__ import annotations

from uuid import uuid4

from sqlalchemy import func, select

from app.crawler.constants import CrawlDispatchState, CrawlJobStatus
from app.crawler.models import CrawlJob
from app.crawler.repository import CrawlerRepository
from app.crawler.schemas import CrawlJobCreate
from app.crawler.service import CrawlerService
from app.db.session import AsyncSessionLocal


async def test_service_reuses_job_by_tenant_idempotency_key() -> None:
    tenant_id = uuid4()
    target_url_id = uuid4()
    async with AsyncSessionLocal() as session:
        repository = CrawlerRepository(session)
        target = await repository.create_target(
            tenant_id=tenant_id,
            target_url_id=target_url_id,
            target_url="https://example.com/a",
            handler_name="example",
        )
        await session.commit()
        assert target.target_host == "example.com"
        payload = CrawlJobCreate(
            tenant_id=tenant_id,
            target_url_id=target_url_id,
            idempotency_key="daily:example",
        )
        first = await CrawlerService(session).create_or_reuse_job(payload)
        second = await CrawlerService(session).create_or_reuse_job(payload)
        count = (await session.execute(select(func.count()).select_from(CrawlJob))).scalar_one()

    assert first.id == second.id
    assert count == 1
    assert first.status == CrawlJobStatus.PENDING
    assert first.dispatch_state == CrawlDispatchState.PENDING


async def test_expired_lease_can_be_reclaimed() -> None:
    tenant_id = uuid4()
    target_url_id = uuid4()
    async with AsyncSessionLocal() as session:
        repository = CrawlerRepository(session)
        target = await repository.create_target(
            tenant_id=tenant_id,
            target_url_id=target_url_id,
            target_url="https://example.com/a",
            handler_name="example",
        )
        job = await repository.create_job(
            tenant_id=tenant_id,
            crawl_target_id=target.id,
            idempotency_key="daily:example",
        )
        await session.commit()

        first = await repository.lease_pending_jobs(limit=1, lease_seconds=-1)
        await session.commit()
        second = await repository.lease_pending_jobs(limit=1, lease_seconds=60)

    assert first[0].id == job.id
    assert second[0].id == job.id
    assert second[0].dispatch_attempts == 2
