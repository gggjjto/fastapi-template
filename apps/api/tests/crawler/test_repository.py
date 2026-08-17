from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.crawler.application.service import CrawlerService
from app.crawler.domain.constants import CrawlDispatchState, CrawlJobStatus
from app.crawler.domain.exceptions import CrawlCancellationUnavailable
from app.crawler.domain.models import CrawlJob
from app.crawler.domain.schemas import CrawlJobCreate
from app.crawler.persistence.repository import CrawlerRepository
from app.db.session import AsyncSessionLocal
from app.tenants.models import Tenant
from app.users.models import User


async def _create_tenant(session: object) -> Tenant:
    user = User(
        email=f"{uuid4()}@example.com",
        full_name="Crawler Owner",
        hashed_password="not-used",
    )
    session.add(user)  # type: ignore[attr-defined]
    await session.flush()  # type: ignore[attr-defined]
    tenant = Tenant(name="Crawler", slug=f"crawler-{uuid4().hex}", created_by=user.id)
    session.add(tenant)  # type: ignore[attr-defined]
    await session.flush()  # type: ignore[attr-defined]
    return tenant


async def _create_job(repository: CrawlerRepository) -> CrawlJob:
    tenant = await _create_tenant(repository.session)
    target = await repository.create_target(
        tenant_id=tenant.id,
        name="Example",
        target_url="https://example.com/a",
        handler_name="http_snapshot",
    )
    return await repository.create_job(
        tenant_id=tenant.id,
        crawl_target_id=target.id,
        idempotency_key="daily:example",
    )


async def test_service_reuses_job_by_tenant_idempotency_key() -> None:
    async with AsyncSessionLocal() as session:
        tenant = await _create_tenant(session)
        repository = CrawlerRepository(session)
        target = await repository.create_target(
            tenant_id=tenant.id,
            name="Example",
            target_url="https://example.com/a",
            handler_name="http_snapshot",
        )
        await session.commit()
        payload = CrawlJobCreate(target_id=target.id, idempotency_key="daily:example")
        first = await CrawlerService(session).create_or_reuse_job(
            tenant_id=tenant.id, payload=payload
        )
        second = await CrawlerService(session).create_or_reuse_job(
            tenant_id=tenant.id, payload=payload
        )
        count = (await session.execute(select(func.count()).select_from(CrawlJob))).scalar_one()

    assert first.id == second.id
    assert count == 1
    assert first.status == CrawlJobStatus.PENDING


async def test_expired_lease_can_be_reclaimed() -> None:
    async with AsyncSessionLocal() as session:
        repository = CrawlerRepository(session)
        job = await _create_job(repository)
        await session.commit()
        first = (await repository.lease_pending_jobs(limit=1, lease_seconds=-1)).leased
        await session.commit()
        second = (await repository.lease_pending_jobs(limit=1, lease_seconds=60)).leased

    assert first[0].id == second[0].id == job.id
    assert second[0].dispatch_attempts == 2


async def test_cancelled_job_is_not_dispatched_or_overwritten() -> None:
    async with AsyncSessionLocal() as session:
        repository = CrawlerRepository(session)
        job = await _create_job(repository)
        await repository.mark_cancelled(job)
        await session.commit()

        assert (await repository.lease_pending_jobs(limit=1, lease_seconds=60)).leased == []
        await repository.mark_succeeded(job, result={"late": True})
        await session.refresh(job)

    assert job.status == CrawlJobStatus.CANCELLED
    assert job.result is None
    assert job.cancel_requested_at is not None


async def test_active_job_is_cancelled_after_remote_confirmation() -> None:
    class Canceller:
        called_with: str | None = None

        async def aio_cancel(self, run_id: str) -> object:
            self.called_with = run_id
            return object()

    async with AsyncSessionLocal() as session:
        repository = CrawlerRepository(session)
        job = await _create_job(repository)
        await session.commit()
        await repository.mark_dispatched(
            job_id=job.id, tenant_id=job.tenant_id, hatchet_run_id="run-1"
        )
        await session.commit()
        canceller = Canceller()

        cancelled = await CrawlerService(session).cancel_job(
            tenant_id=job.tenant_id, job_id=job.id, canceller=canceller
        )

    assert canceller.called_with == "run-1"
    assert cancelled.status == CrawlJobStatus.CANCELLED
    assert cancelled.cancel_requested_at is not None


async def test_active_job_stays_non_terminal_when_remote_cancel_fails() -> None:
    class FailingCanceller:
        async def aio_cancel(self, run_id: str) -> object:
            raise RuntimeError(f"cannot cancel {run_id}")

    async with AsyncSessionLocal() as session:
        repository = CrawlerRepository(session)
        job = await _create_job(repository)
        await session.commit()
        await repository.mark_dispatched(
            job_id=job.id, tenant_id=job.tenant_id, hatchet_run_id="run-2"
        )
        await session.commit()

        with pytest.raises(CrawlCancellationUnavailable):
            await CrawlerService(session).cancel_job(
                tenant_id=job.tenant_id,
                job_id=job.id,
                canceller=FailingCanceller(),
            )
        await session.refresh(job)

    assert job.status == CrawlJobStatus.QUEUED
    assert job.cancel_requested_at is not None


async def test_retry_creates_new_audit_record() -> None:
    async with AsyncSessionLocal() as session:
        repository = CrawlerRepository(session)
        original = await _create_job(repository)
        original.status = CrawlJobStatus.FAILED
        original.dispatch_state = CrawlDispatchState.FAILED
        original.finished_at = datetime.now(UTC)
        await session.commit()

        retried = await CrawlerService(session).retry_job(
            tenant_id=original.tenant_id, job_id=original.id
        )

    assert retried.id != original.id
    assert retried.retry_of_job_id == original.id
    assert retried.status == CrawlJobStatus.PENDING


async def test_metrics_report_lifecycle_percentiles() -> None:
    async with AsyncSessionLocal() as session:
        repository = CrawlerRepository(session)
        job = await _create_job(repository)
        base = datetime.now(UTC) - timedelta(seconds=4)
        job.created_at = base
        job.dispatched_at = base + timedelta(seconds=1)
        job.started_at = base + timedelta(seconds=2)
        job.finished_at = base + timedelta(seconds=4)
        job.status = CrawlJobStatus.SUCCEEDED
        await session.commit()

        metrics = await repository.metrics(
            tenant_id=job.tenant_id,
            from_at=base - timedelta(seconds=1),
            to_at=datetime.now(UTC) + timedelta(seconds=1),
        )

    assert metrics.total == 1
    assert metrics.by_status == {"succeeded": 1}
    assert metrics.dispatch.p50_ms == 1000.0
    assert metrics.run.p95_ms == 2000.0
