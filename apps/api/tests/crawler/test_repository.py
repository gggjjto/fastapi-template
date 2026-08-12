from __future__ import annotations

from uuid import uuid4

from sqlalchemy import func, select

from app.crawler.application.service import CrawlerService
from app.crawler.domain.constants import (
    MAX_DISPATCH_ATTEMPTS,
    CrawlDispatchState,
    CrawlErrorCategory,
    CrawlJobStatus,
)
from app.crawler.domain.models import CrawlJob
from app.crawler.domain.schemas import CrawlJobCreate
from app.crawler.persistence.repository import CrawlerRepository
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


async def test_expired_final_lease_marks_job_failed() -> None:
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

        for attempt in range(1, MAX_DISPATCH_ATTEMPTS + 1):
            leased = await repository.lease_pending_jobs(limit=1, lease_seconds=-1)
            assert leased[0].dispatch_attempts == attempt
            await session.commit()

        exhausted = await repository.lease_pending_jobs(limit=1, lease_seconds=60)
        await session.commit()
        await session.refresh(job)

    assert exhausted == []
    assert job.dispatch_attempts == MAX_DISPATCH_ATTEMPTS
    assert job.dispatch_state == CrawlDispatchState.FAILED
    assert job.status == CrawlJobStatus.FAILED
    assert job.error_category == CrawlErrorCategory.TRANSIENT
    assert job.error_code == "DISPATCH_LEASE_EXHAUSTED"
    assert job.dispatch_lease_until is None
