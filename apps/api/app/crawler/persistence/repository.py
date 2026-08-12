from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawler.domain.constants import (
    MAX_DISPATCH_ATTEMPTS,
    CrawlDispatchState,
    CrawlErrorCategory,
    CrawlJobStatus,
)
from app.crawler.domain.models import CrawlJob, CrawlTarget


@dataclass(frozen=True, slots=True)
class LeasedCrawlJob:
    id: uuid.UUID
    tenant_id: uuid.UUID
    target_url_id: uuid.UUID
    target_host: str
    dispatch_attempts: int


class CrawlerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_target(
        self, *, tenant_id: uuid.UUID, target_url_id: uuid.UUID
    ) -> CrawlTarget | None:
        result = await self.session.execute(
            select(CrawlTarget).where(
                CrawlTarget.tenant_id == tenant_id,
                CrawlTarget.target_url_id == target_url_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_target(
        self,
        *,
        tenant_id: uuid.UUID,
        target_url_id: uuid.UUID,
        target_url: str,
        handler_name: str,
    ) -> CrawlTarget:
        parsed = urlsplit(target_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("crawler target must be an absolute HTTP(S) URL")
        target = CrawlTarget(
            tenant_id=tenant_id,
            target_url_id=target_url_id,
            target_url=target_url,
            target_host=parsed.hostname,
            handler_name=handler_name,
        )
        self.session.add(target)
        await self.session.flush()
        return target

    async def get_job_by_idempotency_key(
        self, *, tenant_id: uuid.UUID, idempotency_key: str
    ) -> CrawlJob | None:
        result = await self.session.execute(
            select(CrawlJob).where(
                CrawlJob.tenant_id == tenant_id,
                CrawlJob.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def create_job(
        self, *, tenant_id: uuid.UUID, crawl_target_id: uuid.UUID, idempotency_key: str
    ) -> CrawlJob:
        job = CrawlJob(
            tenant_id=tenant_id,
            crawl_target_id=crawl_target_id,
            idempotency_key=idempotency_key,
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def lease_pending_jobs(self, *, limit: int, lease_seconds: int) -> list[LeasedCrawlJob]:
        now = datetime.now(UTC)
        eligible = or_(
            CrawlJob.dispatch_state == CrawlDispatchState.PENDING,
            (
                (CrawlJob.dispatch_state == CrawlDispatchState.LEASED)
                & (CrawlJob.dispatch_lease_until < now)
            ),
        )
        rows = (
            await self.session.execute(
                select(CrawlJob, CrawlTarget)
                .join(CrawlTarget, CrawlTarget.id == CrawlJob.crawl_target_id)
                .where(
                    eligible,
                    or_(CrawlJob.next_dispatch_at.is_(None), CrawlJob.next_dispatch_at <= now),
                )
                .order_by(CrawlJob.created_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        ).all()
        leased_until = now + timedelta(seconds=lease_seconds)
        leased: list[LeasedCrawlJob] = []
        for job, target in rows:
            if job.dispatch_attempts >= MAX_DISPATCH_ATTEMPTS:
                job.dispatch_state = CrawlDispatchState.FAILED
                job.status = CrawlJobStatus.FAILED
                job.error_category = CrawlErrorCategory.TRANSIENT
                job.error_code = "DISPATCH_LEASE_EXHAUSTED"
                job.error_message = "Crawler dispatch lease expired after maximum attempts"
                job.dispatch_lease_until = None
                job.next_dispatch_at = None
                continue
            job.dispatch_state = CrawlDispatchState.LEASED
            job.dispatch_attempts += 1
            job.dispatch_lease_until = leased_until
            leased.append(
                LeasedCrawlJob(
                    id=job.id,
                    tenant_id=job.tenant_id,
                    target_url_id=target.target_url_id,
                    target_host=target.target_host,
                    dispatch_attempts=job.dispatch_attempts,
                )
            )
        await self.session.flush()
        return leased

    async def mark_dispatched(
        self, *, job_id: uuid.UUID, tenant_id: uuid.UUID, hatchet_run_id: str
    ) -> bool:
        job = await self._get_job(job_id=job_id, tenant_id=tenant_id)
        if job is None:
            return False
        if job.hatchet_run_id and job.hatchet_run_id != hatchet_run_id:
            job.dispatch_state = CrawlDispatchState.FAILED
            job.status = CrawlJobStatus.FAILED
            job.error_category = CrawlErrorCategory.PERMANENT
            job.error_code = "HATCHET_RUN_ID_CONFLICT"
            job.dispatch_lease_until = None
            return False
        job.hatchet_run_id = hatchet_run_id
        job.dispatch_state = CrawlDispatchState.DISPATCHED
        job.status = CrawlJobStatus.QUEUED
        job.dispatch_lease_until = None
        job.next_dispatch_at = None
        return True

    async def record_dispatch_failure(
        self, *, job_id: uuid.UUID, tenant_id: uuid.UUID, error: str
    ) -> None:
        job = await self._get_job(job_id=job_id, tenant_id=tenant_id)
        if job is None:
            return
        job.error_category = CrawlErrorCategory.TRANSIENT
        job.error_code = "DISPATCH_FAILED"
        job.error_message = error[:2000]
        job.dispatch_lease_until = None
        if job.dispatch_attempts >= MAX_DISPATCH_ATTEMPTS:
            job.dispatch_state = CrawlDispatchState.FAILED
            job.status = CrawlJobStatus.FAILED
            return
        job.dispatch_state = CrawlDispatchState.PENDING
        job.status = CrawlJobStatus.PENDING
        delay = min(5 * 2 ** (job.dispatch_attempts - 1), 300)
        job.next_dispatch_at = datetime.now(UTC) + timedelta(seconds=delay)

    async def load_for_execution(
        self,
        *,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        target_url_id: uuid.UUID,
    ) -> tuple[CrawlJob, CrawlTarget] | None:
        result = await self.session.execute(
            select(CrawlJob, CrawlTarget)
            .join(CrawlTarget, CrawlTarget.id == CrawlJob.crawl_target_id)
            .where(
                CrawlJob.id == job_id,
                CrawlJob.tenant_id == tenant_id,
                CrawlTarget.tenant_id == tenant_id,
                CrawlTarget.target_url_id == target_url_id,
            )
        )
        row = result.one_or_none()
        return None if row is None else (row[0], row[1])

    async def mark_running(self, job: CrawlJob, *, attempt_count: int) -> None:
        job.status = CrawlJobStatus.RUNNING
        job.attempt_count = attempt_count
        job.error_category = None
        job.error_code = None
        job.error_message = None
        await self.session.commit()

    async def mark_retrying(self, job: CrawlJob, *, error: Exception) -> None:
        job.status = CrawlJobStatus.RETRYING
        job.error_category = CrawlErrorCategory.TRANSIENT
        job.error_code = error.__class__.__name__
        job.error_message = str(error)[:2000]
        await self.session.commit()

    async def mark_succeeded(self, job: CrawlJob, *, result: dict[str, Any]) -> None:
        job.status = CrawlJobStatus.SUCCEEDED
        job.result = result
        await self.session.commit()

    async def mark_failed(
        self,
        job: CrawlJob,
        *,
        error: Exception,
        category: CrawlErrorCategory,
    ) -> None:
        job.status = CrawlJobStatus.FAILED
        job.error_category = category
        job.error_code = error.__class__.__name__
        job.error_message = str(error)[:2000]
        await self.session.commit()

    async def _get_job(self, *, job_id: uuid.UUID, tenant_id: uuid.UUID) -> CrawlJob | None:
        result = await self.session.execute(
            select(CrawlJob).where(CrawlJob.id == job_id, CrawlJob.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()
