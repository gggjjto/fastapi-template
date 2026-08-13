from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import func, select

import app.crawler.application.service as service_module
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


async def _create_job(repository: CrawlerRepository) -> CrawlJob:
    tenant_id = uuid4()
    target = await repository.create_target(
        tenant_id=tenant_id,
        target_url_id=uuid4(),
        target_url="https://example.com/a",
        handler_name="example",
    )
    return await repository.create_job(
        tenant_id=tenant_id,
        crawl_target_id=target.id,
        idempotency_key="daily:example",
    )


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


async def test_service_logs_created_job_without_sensitive_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[tuple[str, dict[str, Any]]] = []

    class FakeLogger:
        def info(self, event: str, **kwargs: Any) -> None:
            captured.append((event, kwargs))

    monkeypatch.setattr(service_module, "logger", FakeLogger(), raising=False)

    tenant_id = uuid4()
    target_url_id = uuid4()
    async with AsyncSessionLocal() as session:
        repository = CrawlerRepository(session)
        await repository.create_target(
            tenant_id=tenant_id,
            target_url_id=target_url_id,
            target_url="https://example.com/secret-token",
            handler_name="example",
        )
        await session.commit()

        job = await CrawlerService(session).create_or_reuse_job(
            CrawlJobCreate(
                tenant_id=tenant_id,
                target_url_id=target_url_id,
                idempotency_key="secret-idempotency-key",
            )
        )

    assert captured == [
        (
            "crawler.job.created",
            {
                "crawl_job_id": str(job.id),
                "handler_name": "example",
                "target_host": "example.com",
            },
        )
    ]
    assert "secret" not in str(captured)


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

        first = (await repository.lease_pending_jobs(limit=1, lease_seconds=-1)).leased
        await session.commit()
        second = (await repository.lease_pending_jobs(limit=1, lease_seconds=60)).leased

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
            leased = (await repository.lease_pending_jobs(limit=1, lease_seconds=-1)).leased
            assert leased[0].dispatch_attempts == attempt
            await session.commit()

        exhausted = await repository.lease_pending_jobs(limit=1, lease_seconds=60)
        await session.commit()
        await session.refresh(job)

    assert exhausted.leased == []
    assert len(exhausted.exhausted) == 1
    assert job.dispatch_attempts == MAX_DISPATCH_ATTEMPTS
    assert job.dispatch_state == CrawlDispatchState.FAILED
    assert job.status == CrawlJobStatus.FAILED
    assert job.error_category == CrawlErrorCategory.TRANSIENT
    assert job.error_code == "DISPATCH_LEASE_EXHAUSTED"
    assert job.dispatch_lease_until is None


async def test_mark_dispatched_sets_dispatched_at() -> None:
    async with AsyncSessionLocal() as session:
        repository = CrawlerRepository(session)
        job = await _create_job(repository)
        await session.commit()

        marked = await repository.mark_dispatched(
            job_id=job.id,
            tenant_id=job.tenant_id,
            hatchet_run_id="run-1",
        )
        await session.commit()
        await session.refresh(job)

    assert marked is job
    assert job.dispatched_at is not None


async def test_mark_running_sets_started_at_once() -> None:
    async with AsyncSessionLocal() as session:
        repository = CrawlerRepository(session)
        job = await _create_job(repository)
        await repository.mark_running(job, attempt_count=1)
        first_started_at = job.started_at

        await repository.mark_retrying(job, error=RuntimeError("timeout"))
        await repository.mark_running(job, attempt_count=2)
        await session.refresh(job)

    assert first_started_at is not None
    assert job.started_at is not None
    assert job.started_at.replace(tzinfo=UTC) == first_started_at.replace(tzinfo=UTC)


async def test_mark_succeeded_sets_finished_at() -> None:
    async with AsyncSessionLocal() as session:
        repository = CrawlerRepository(session)
        job = await _create_job(repository)
        job.dispatch_lease_until = datetime.now(UTC) + timedelta(minutes=1)
        job.next_dispatch_at = datetime.now(UTC) + timedelta(minutes=1)

        await repository.mark_succeeded(job, result={"ok": True})
        await session.refresh(job)

    assert job.finished_at is not None
    assert job.dispatch_lease_until is None
    assert job.next_dispatch_at is None


async def test_mark_failed_sets_finished_at() -> None:
    async with AsyncSessionLocal() as session:
        repository = CrawlerRepository(session)
        job = await _create_job(repository)
        job.dispatch_lease_until = datetime.now(UTC) + timedelta(minutes=1)
        job.next_dispatch_at = datetime.now(UTC) + timedelta(minutes=1)

        await repository.mark_failed(
            job,
            error=RuntimeError("invalid"),
            category=CrawlErrorCategory.PERMANENT,
        )
        await session.refresh(job)

    assert job.finished_at is not None
    assert job.dispatch_lease_until is None
    assert job.next_dispatch_at is None


async def test_final_dispatch_failure_sets_finished_at() -> None:
    async with AsyncSessionLocal() as session:
        repository = CrawlerRepository(session)
        job = await _create_job(repository)
        job.dispatch_attempts = MAX_DISPATCH_ATTEMPTS
        job.dispatch_lease_until = datetime.now(UTC) + timedelta(minutes=1)
        job.next_dispatch_at = datetime.now(UTC) + timedelta(minutes=1)

        await repository.record_dispatch_failure(
            job_id=job.id,
            tenant_id=job.tenant_id,
            error="hatchet unavailable",
        )
        await session.commit()
        await session.refresh(job)

    assert job.status == CrawlJobStatus.FAILED
    assert job.finished_at is not None
    assert job.dispatch_lease_until is None
    assert job.next_dispatch_at is None


async def test_dispatch_run_id_conflict_sets_finished_at() -> None:
    async with AsyncSessionLocal() as session:
        repository = CrawlerRepository(session)
        job = await _create_job(repository)
        job.hatchet_run_id = "run-1"
        job.dispatch_lease_until = datetime.now(UTC) + timedelta(minutes=1)
        job.next_dispatch_at = datetime.now(UTC) + timedelta(minutes=1)
        await session.commit()

        marked = await repository.mark_dispatched(
            job_id=job.id,
            tenant_id=job.tenant_id,
            hatchet_run_id="run-2",
        )
        await session.commit()
        await session.refresh(job)

    assert marked is job
    assert job.status == CrawlJobStatus.FAILED
    assert job.finished_at is not None
    assert job.dispatch_lease_until is None
    assert job.next_dispatch_at is None


async def test_expired_final_lease_sets_finished_at() -> None:
    async with AsyncSessionLocal() as session:
        repository = CrawlerRepository(session)
        job = await _create_job(repository)
        job.dispatch_state = CrawlDispatchState.LEASED
        job.dispatch_attempts = MAX_DISPATCH_ATTEMPTS
        job.dispatch_lease_until = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()

        leased = await repository.lease_pending_jobs(limit=1, lease_seconds=60)
        await session.commit()
        await session.refresh(job)

    assert leased.leased == []
    assert len(leased.exhausted) == 1
    assert job.status == CrawlJobStatus.FAILED
    assert job.finished_at is not None
    assert job.dispatch_lease_until is None
    assert job.next_dispatch_at is None
