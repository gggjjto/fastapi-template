from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from urllib.parse import urlsplit

from sqlalchemy import case, func, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.crawler.domain.constants import (
    MAX_DISPATCH_ATTEMPTS,
    CrawlDispatchState,
    CrawlErrorCategory,
    CrawlJobStatus,
)
from app.crawler.domain.models import CrawlJob, CrawlTarget
from app.crawler.domain.schemas import CrawlMetricDurations, CrawlMetrics


@dataclass(frozen=True, slots=True)
class LeasedCrawlJob:
    id: uuid.UUID
    tenant_id: uuid.UUID
    target_host: str
    handler_name: str
    dispatch_attempts: int


@dataclass(frozen=True, slots=True)
class ExhaustedDispatchJob:
    id: uuid.UUID
    handler_name: str
    target_host: str
    dispatch_attempts: int
    job_age_ms: float


@dataclass(frozen=True, slots=True)
class DispatchLeaseBatch:
    leased: list[LeasedCrawlJob]
    exhausted: list[ExhaustedDispatchJob]


class CrawlerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_target(self, *, tenant_id: uuid.UUID, target_id: uuid.UUID) -> CrawlTarget | None:
        result = await self.session.execute(
            select(CrawlTarget).where(
                CrawlTarget.id == target_id,
                CrawlTarget.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_targets(
        self, *, tenant_id: uuid.UUID, limit: int, offset: int
    ) -> tuple[list[CrawlTarget], int]:
        where = (CrawlTarget.tenant_id == tenant_id, CrawlTarget.archived_at.is_(None))
        total = (
            await self.session.execute(select(func.count()).select_from(CrawlTarget).where(*where))
        ).scalar_one()
        rows = await self.session.execute(
            select(CrawlTarget)
            .where(*where)
            .order_by(CrawlTarget.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(rows.scalars()), total

    async def create_target(
        self,
        *,
        tenant_id: uuid.UUID,
        name: str,
        target_url: str,
        handler_name: str,
        enabled: bool = True,
        schedule_cron: str | None = None,
        schedule_timezone: str = "UTC",
        schedule_enabled: bool = False,
        next_run_at: datetime | None = None,
    ) -> CrawlTarget:
        target_host = _target_host(target_url)
        target = CrawlTarget(
            tenant_id=tenant_id,
            name=name,
            target_url=target_url,
            target_host=target_host,
            handler_name=handler_name,
            enabled=enabled,
            schedule_cron=schedule_cron,
            schedule_timezone=schedule_timezone,
            schedule_enabled=schedule_enabled,
            next_run_at=next_run_at,
        )
        self.session.add(target)
        await self.session.flush()
        return target

    async def update_target(self, target: CrawlTarget, changes: dict[str, object]) -> CrawlTarget:
        if "target_url" in changes:
            target.target_host = _target_host(str(changes["target_url"]))
        for name, value in changes.items():
            setattr(target, name, value)
        await self.session.flush()
        return target

    async def archive_target(self, target: CrawlTarget) -> CrawlTarget:
        target.archived_at = datetime.now(UTC)
        target.enabled = False
        target.schedule_enabled = False
        target.next_run_at = None
        await self.session.flush()
        return target

    async def lease_due_targets(self, *, now: datetime, limit: int) -> list[CrawlTarget]:
        rows = await self.session.execute(
            select(CrawlTarget)
            .where(
                CrawlTarget.enabled.is_(True),
                CrawlTarget.schedule_enabled.is_(True),
                CrawlTarget.archived_at.is_(None),
                CrawlTarget.schedule_cron.is_not(None),
                CrawlTarget.next_run_at <= now,
            )
            .order_by(CrawlTarget.next_run_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(rows.scalars())

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

    async def get_job(self, *, tenant_id: uuid.UUID, job_id: uuid.UUID) -> CrawlJob | None:
        return await self._get_job(job_id=job_id, tenant_id=tenant_id)

    async def list_jobs(
        self,
        *,
        tenant_id: uuid.UUID,
        limit: int,
        offset: int,
        target_id: uuid.UUID | None = None,
        status: CrawlJobStatus | None = None,
        handler_name: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[CrawlJob], int]:
        filters: list[ColumnElement[bool]] = [CrawlJob.tenant_id == tenant_id]
        if target_id is not None:
            filters.append(CrawlJob.crawl_target_id == target_id)
        if status is not None:
            filters.append(CrawlJob.status == status)
        if handler_name is not None:
            filters.append(CrawlTarget.handler_name == handler_name)
        if created_from is not None:
            filters.append(CrawlJob.created_at >= created_from)
        if created_to is not None:
            filters.append(CrawlJob.created_at <= created_to)
        base = select(CrawlJob).join(CrawlTarget, CrawlTarget.id == CrawlJob.crawl_target_id)
        total = (
            await self.session.execute(
                select(func.count()).select_from(base.where(*filters).subquery())
            )
        ).scalar_one()
        rows = await self.session.execute(
            base.where(*filters).order_by(CrawlJob.created_at.desc()).limit(limit).offset(offset)
        )
        return list(rows.scalars()), total

    async def create_job(
        self,
        *,
        tenant_id: uuid.UUID,
        crawl_target_id: uuid.UUID,
        idempotency_key: str,
        scheduled_for: datetime | None = None,
        retry_of_job_id: uuid.UUID | None = None,
    ) -> CrawlJob:
        job = CrawlJob(
            tenant_id=tenant_id,
            crawl_target_id=crawl_target_id,
            idempotency_key=idempotency_key,
            scheduled_for=scheduled_for,
            retry_of_job_id=retry_of_job_id,
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def lease_pending_jobs(self, *, limit: int, lease_seconds: int) -> DispatchLeaseBatch:
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
                    CrawlJob.status != CrawlJobStatus.CANCELLED,
                    or_(CrawlJob.next_dispatch_at.is_(None), CrawlJob.next_dispatch_at <= now),
                )
                .order_by(CrawlJob.created_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        ).all()
        leased_until = now + timedelta(seconds=lease_seconds)
        leased: list[LeasedCrawlJob] = []
        exhausted: list[ExhaustedDispatchJob] = []
        for job, target in rows:
            if job.dispatch_attempts >= MAX_DISPATCH_ATTEMPTS:
                finished_at = datetime.now(UTC)
                job.dispatch_state = CrawlDispatchState.FAILED
                job.status = CrawlJobStatus.FAILED
                job.error_category = CrawlErrorCategory.TRANSIENT
                job.error_code = "DISPATCH_LEASE_EXHAUSTED"
                job.error_message = "Crawler dispatch lease expired after maximum attempts"
                self._finish_job(job, finished_at=finished_at)
                exhausted.append(
                    ExhaustedDispatchJob(
                        id=job.id,
                        handler_name=target.handler_name,
                        target_host=target.target_host,
                        dispatch_attempts=job.dispatch_attempts,
                        job_age_ms=_duration_ms(job.created_at, finished_at),
                    )
                )
                continue
            job.dispatch_state = CrawlDispatchState.LEASED
            job.dispatch_attempts += 1
            job.dispatch_lease_until = leased_until
            leased.append(
                LeasedCrawlJob(
                    id=job.id,
                    tenant_id=job.tenant_id,
                    target_host=target.target_host,
                    handler_name=target.handler_name,
                    dispatch_attempts=job.dispatch_attempts,
                )
            )
        await self.session.flush()
        return DispatchLeaseBatch(leased=leased, exhausted=exhausted)

    async def mark_dispatched(
        self, *, job_id: uuid.UUID, tenant_id: uuid.UUID, hatchet_run_id: str
    ) -> CrawlJob | None:
        job = await self._get_job(job_id=job_id, tenant_id=tenant_id)
        if job is None or job.status == CrawlJobStatus.CANCELLED:
            return job
        if job.hatchet_run_id and job.hatchet_run_id != hatchet_run_id:
            job.dispatch_state = CrawlDispatchState.FAILED
            job.status = CrawlJobStatus.FAILED
            job.error_category = CrawlErrorCategory.PERMANENT
            job.error_code = "HATCHET_RUN_ID_CONFLICT"
            self._finish_job(job)
            return job
        dispatched_at = datetime.now(UTC)
        job.hatchet_run_id = hatchet_run_id
        job.dispatch_state = CrawlDispatchState.DISPATCHED
        job.status = CrawlJobStatus.QUEUED
        job.dispatch_lease_until = None
        job.next_dispatch_at = None
        if job.dispatched_at is None:
            job.dispatched_at = dispatched_at
        return job

    async def record_dispatch_failure(
        self, *, job_id: uuid.UUID, tenant_id: uuid.UUID, error: str
    ) -> CrawlJob | None:
        job = await self._get_job(job_id=job_id, tenant_id=tenant_id)
        if job is None or job.status == CrawlJobStatus.CANCELLED:
            return job
        job.error_category = CrawlErrorCategory.TRANSIENT
        job.error_code = "DISPATCH_FAILED"
        job.error_message = error[:2000]
        job.dispatch_lease_until = None
        if job.dispatch_attempts >= MAX_DISPATCH_ATTEMPTS:
            job.dispatch_state = CrawlDispatchState.FAILED
            job.status = CrawlJobStatus.FAILED
            self._finish_job(job)
            return job
        job.dispatch_state = CrawlDispatchState.PENDING
        job.status = CrawlJobStatus.PENDING
        delay = min(5 * 2 ** (job.dispatch_attempts - 1), 300)
        job.next_dispatch_at = datetime.now(UTC) + timedelta(seconds=delay)
        return job

    async def load_for_execution(self, *, job_id: uuid.UUID) -> tuple[CrawlJob, CrawlTarget] | None:
        result = await self.session.execute(
            select(CrawlJob, CrawlTarget)
            .join(CrawlTarget, CrawlTarget.id == CrawlJob.crawl_target_id)
            .where(CrawlJob.id == job_id, CrawlTarget.tenant_id == CrawlJob.tenant_id)
        )
        row = result.one_or_none()
        return None if row is None else (row[0], row[1])

    async def mark_running(self, job: CrawlJob, *, attempt_count: int) -> bool:
        result = cast(
            CursorResult[Any],
            await self.session.execute(
                update(CrawlJob)
                .where(CrawlJob.id == job.id, CrawlJob.status != CrawlJobStatus.CANCELLED)
                .values(
                    status=CrawlJobStatus.RUNNING,
                    attempt_count=attempt_count,
                    started_at=case(
                        (CrawlJob.started_at.is_(None), datetime.now(UTC)),
                        else_=CrawlJob.started_at,
                    ),
                    error_category=None,
                    error_code=None,
                    error_message=None,
                )
            ),
        )
        await self.session.commit()
        await self.session.refresh(job)
        return bool(result.rowcount)

    async def mark_retrying(self, job: CrawlJob, *, error: Exception) -> None:
        await self.session.execute(
            update(CrawlJob)
            .where(CrawlJob.id == job.id, CrawlJob.status != CrawlJobStatus.CANCELLED)
            .values(
                status=CrawlJobStatus.RETRYING,
                error_category=CrawlErrorCategory.TRANSIENT,
                error_code=error.__class__.__name__,
                error_message=str(error)[:2000],
            )
        )
        await self.session.commit()
        await self.session.refresh(job)

    async def mark_succeeded(self, job: CrawlJob, *, result: dict[str, Any]) -> None:
        await self.session.execute(
            update(CrawlJob)
            .where(CrawlJob.id == job.id, CrawlJob.status != CrawlJobStatus.CANCELLED)
            .values(
                status=CrawlJobStatus.SUCCEEDED,
                result=result,
                dispatch_lease_until=None,
                next_dispatch_at=None,
                finished_at=datetime.now(UTC),
            )
        )
        await self.session.commit()
        await self.session.refresh(job)

    async def mark_failed(
        self,
        job: CrawlJob,
        *,
        error: Exception,
        category: CrawlErrorCategory,
    ) -> None:
        await self.session.execute(
            update(CrawlJob)
            .where(CrawlJob.id == job.id, CrawlJob.status != CrawlJobStatus.CANCELLED)
            .values(
                status=CrawlJobStatus.FAILED,
                error_category=category,
                error_code=error.__class__.__name__,
                error_message=str(error)[:2000],
                dispatch_lease_until=None,
                next_dispatch_at=None,
                finished_at=datetime.now(UTC),
            )
        )
        await self.session.commit()
        await self.session.refresh(job)

    async def mark_cancelled(self, job: CrawlJob) -> CrawlJob:
        now = datetime.now(UTC)
        job.cancel_requested_at = now
        job.status = CrawlJobStatus.CANCELLED
        self._finish_job(job, finished_at=now)
        await self.session.flush()
        return job

    async def mark_cancel_requested(self, job: CrawlJob) -> CrawlJob:
        job.cancel_requested_at = datetime.now(UTC)
        await self.session.flush()
        return job

    async def metrics(
        self, *, tenant_id: uuid.UUID, from_at: datetime, to_at: datetime
    ) -> CrawlMetrics:
        rows = list(
            (
                await self.session.execute(
                    select(CrawlJob).where(
                        CrawlJob.tenant_id == tenant_id,
                        CrawlJob.created_at >= from_at,
                        CrawlJob.created_at <= to_at,
                    )
                )
            ).scalars()
        )
        by_status: dict[str, int] = {}
        for job in rows:
            by_status[job.status] = by_status.get(job.status, 0) + 1
        return CrawlMetrics(
            from_at=from_at,
            to_at=to_at,
            total=len(rows),
            errors=sum(job.status == CrawlJobStatus.FAILED for job in rows),
            by_status=by_status,
            dispatch=_percentiles(
                [
                    _duration_ms(job.created_at, job.dispatched_at)
                    for job in rows
                    if job.dispatched_at
                ]
            ),
            queue=_percentiles(
                [
                    _duration_ms(job.dispatched_at, job.started_at)
                    for job in rows
                    if job.dispatched_at and job.started_at
                ]
            ),
            run=_percentiles(
                [
                    _duration_ms(job.started_at, job.finished_at)
                    for job in rows
                    if job.started_at and job.finished_at
                ]
            ),
            total_duration=_percentiles(
                [_duration_ms(job.created_at, job.finished_at) for job in rows if job.finished_at]
            ),
        )

    @staticmethod
    def _finish_job(job: CrawlJob, *, finished_at: datetime | None = None) -> None:
        job.dispatch_lease_until = None
        job.next_dispatch_at = None
        job.finished_at = finished_at or datetime.now(UTC)

    async def _get_job(self, *, job_id: uuid.UUID, tenant_id: uuid.UUID) -> CrawlJob | None:
        result = await self.session.execute(
            select(CrawlJob).where(CrawlJob.id == job_id, CrawlJob.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()


def _target_host(target_url: str) -> str:
    parsed = urlsplit(target_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("crawler target must be an absolute HTTP(S) URL")
    return parsed.hostname


def _duration_ms(start: datetime, end: datetime) -> float:
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    return round((end - start).total_seconds() * 1000, 2)


def _percentiles(values: list[float]) -> CrawlMetricDurations:
    if not values:
        return CrawlMetricDurations(p50_ms=None, p95_ms=None)
    ordered = sorted(values)

    def percentile(value: float) -> float:
        index = max(0, math.ceil(value * len(ordered)) - 1)
        return ordered[index]

    return CrawlMetricDurations(p50_ms=percentile(0.5), p95_ms=percentile(0.95))
