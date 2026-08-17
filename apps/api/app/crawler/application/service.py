from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import structlog
from croniter import CroniterBadCronError, croniter
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawler.domain.constants import CrawlJobStatus
from app.crawler.domain.exceptions import (
    CrawlCancellationUnavailable,
    CrawlHandlerNotFound,
    CrawlJobConflict,
    CrawlJobInvalidState,
    CrawlJobNotFound,
    CrawlTargetInvalid,
    CrawlTargetNotFound,
)
from app.crawler.domain.models import CrawlJob, CrawlTarget
from app.crawler.domain.schemas import (
    CrawlJobCreate,
    CrawlMetrics,
    CrawlTargetCreate,
    CrawlTargetUpdate,
)
from app.crawler.persistence.repository import CrawlerRepository
from app.crawler.runtime.registry import discover_handlers, registry

logger = structlog.get_logger(__name__)


class CrawlRunCanceller(Protocol):
    async def aio_cancel(self, run_id: str) -> object: ...


class CrawlerService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = CrawlerRepository(session)

    async def list_targets(
        self, *, tenant_id: uuid.UUID, limit: int, offset: int
    ) -> tuple[list[CrawlTarget], int]:
        return await self.repository.list_targets(tenant_id=tenant_id, limit=limit, offset=offset)

    async def get_target(self, *, tenant_id: uuid.UUID, target_id: uuid.UUID) -> CrawlTarget:
        target = await self.repository.get_target(tenant_id=tenant_id, target_id=target_id)
        if target is None:
            raise CrawlTargetNotFound()
        return target

    async def create_target(
        self, *, tenant_id: uuid.UUID, payload: CrawlTargetCreate
    ) -> CrawlTarget:
        self._require_handler(payload.handler_name)
        next_run_at = (
            _next_cron_time(payload.schedule_cron, payload.schedule_timezone)
            if payload.schedule_enabled
            else None
        )
        try:
            try:
                target = await self.repository.create_target(
                    tenant_id=tenant_id,
                    next_run_at=next_run_at,
                    **payload.model_dump(),
                )
            except ValueError as exc:
                raise CrawlTargetInvalid(str(exc)) from exc
            await self.session.commit()
            await self.session.refresh(target)
            return target
        except IntegrityError as exc:
            await self.session.rollback()
            raise CrawlJobConflict("Crawler target URL already exists in this tenant") from exc

    async def update_target(
        self, *, tenant_id: uuid.UUID, target_id: uuid.UUID, payload: CrawlTargetUpdate
    ) -> CrawlTarget:
        target = await self.get_target(tenant_id=tenant_id, target_id=target_id)
        if target.archived_at is not None:
            raise CrawlTargetNotFound()
        changes = payload.model_dump(exclude_unset=True)
        handler_name = changes.get("handler_name")
        if isinstance(handler_name, str):
            self._require_handler(handler_name)
        cron = changes.get("schedule_cron", target.schedule_cron)
        timezone_name = str(changes.get("schedule_timezone", target.schedule_timezone))
        enabled = bool(changes.get("schedule_enabled", target.schedule_enabled))
        if enabled and not cron:
            raise CrawlTargetInvalid("schedule_cron is required when scheduling is enabled")
        changes["next_run_at"] = _next_cron_time(str(cron), timezone_name) if enabled else None
        try:
            updated = await self.repository.update_target(target, changes)
        except ValueError as exc:
            raise CrawlTargetInvalid(str(exc)) from exc
        await self.session.commit()
        await self.session.refresh(updated)
        return updated

    async def archive_target(self, *, tenant_id: uuid.UUID, target_id: uuid.UUID) -> CrawlTarget:
        target = await self.get_target(tenant_id=tenant_id, target_id=target_id)
        if target.archived_at is None:
            await self.repository.archive_target(target)
            await self.session.commit()
            await self.session.refresh(target)
        return target

    async def create_or_reuse_job(
        self, *, tenant_id: uuid.UUID, payload: CrawlJobCreate
    ) -> CrawlJob:
        existing = await self.repository.get_job_by_idempotency_key(
            tenant_id=tenant_id,
            idempotency_key=payload.idempotency_key,
        )
        if existing is not None:
            return existing
        target = await self.repository.get_target(tenant_id=tenant_id, target_id=payload.target_id)
        if target is None or not target.enabled or target.archived_at is not None:
            raise CrawlTargetNotFound()
        return await self._create_job(
            tenant_id=tenant_id,
            target=target,
            idempotency_key=payload.idempotency_key,
        )

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
        return await self.repository.list_jobs(
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
            target_id=target_id,
            status=status,
            handler_name=handler_name,
            created_from=created_from,
            created_to=created_to,
        )

    async def get_job(self, *, tenant_id: uuid.UUID, job_id: uuid.UUID) -> CrawlJob:
        job = await self.repository.get_job(tenant_id=tenant_id, job_id=job_id)
        if job is None:
            raise CrawlJobNotFound()
        return job

    async def cancel_job(
        self,
        *,
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        canceller: CrawlRunCanceller | None,
    ) -> CrawlJob:
        job = await self.get_job(tenant_id=tenant_id, job_id=job_id)
        if job.status in CrawlJobStatus.terminal():
            raise CrawlJobInvalidState("Terminal crawl jobs cannot be cancelled")
        run_id = job.hatchet_run_id
        if run_id:
            await self.repository.mark_cancel_requested(job)
            await self.session.commit()
            if canceller is None:
                raise CrawlCancellationUnavailable()
            try:
                await canceller.aio_cancel(run_id)
            except Exception as exc:
                logger.exception("crawler.job.remote_cancel_failed", crawl_job_id=str(job.id))
                raise CrawlCancellationUnavailable() from exc
            await self.session.refresh(job)
            if job.status in CrawlJobStatus.terminal():
                raise CrawlJobInvalidState("Crawl job finished before cancellation completed")
        await self.repository.mark_cancelled(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def retry_job(self, *, tenant_id: uuid.UUID, job_id: uuid.UUID) -> CrawlJob:
        original = await self.get_job(tenant_id=tenant_id, job_id=job_id)
        if original.status not in {CrawlJobStatus.FAILED, CrawlJobStatus.CANCELLED}:
            raise CrawlJobInvalidState("Only failed or cancelled crawl jobs can be retried")
        target = await self.repository.get_target(
            tenant_id=tenant_id, target_id=original.crawl_target_id
        )
        if target is None or not target.enabled or target.archived_at is not None:
            raise CrawlTargetNotFound()
        return await self._create_job(
            tenant_id=tenant_id,
            target=target,
            idempotency_key=f"retry:{original.id}:{uuid.uuid4().hex}",
            retry_of_job_id=original.id,
        )

    async def metrics(
        self, *, tenant_id: uuid.UUID, from_at: datetime, to_at: datetime
    ) -> CrawlMetrics:
        if to_at <= from_at or to_at - from_at > timedelta(days=31):
            raise CrawlTargetInvalid("metrics range must be positive and no longer than 31 days")
        return await self.repository.metrics(tenant_id=tenant_id, from_at=from_at, to_at=to_at)

    async def _create_job(
        self,
        *,
        tenant_id: uuid.UUID,
        target: CrawlTarget,
        idempotency_key: str,
        retry_of_job_id: uuid.UUID | None = None,
    ) -> CrawlJob:
        try:
            job = await self.repository.create_job(
                tenant_id=tenant_id,
                crawl_target_id=target.id,
                idempotency_key=idempotency_key,
                retry_of_job_id=retry_of_job_id,
            )
            await self.session.commit()
            await self.session.refresh(job)
            logger.info(
                "crawler.job.created",
                crawl_job_id=str(job.id),
                handler_name=target.handler_name,
                target_host=target.target_host,
            )
            return job
        except IntegrityError as exc:
            await self.session.rollback()
            existing = await self.repository.get_job_by_idempotency_key(
                tenant_id=tenant_id, idempotency_key=idempotency_key
            )
            if existing is not None:
                return existing
            raise CrawlJobConflict() from exc

    @staticmethod
    def _require_handler(handler_name: str) -> None:
        if not registry.values():
            discover_handlers()
        if handler_name not in registry.values():
            raise CrawlHandlerNotFound(handler_name)


def _next_cron_time(
    expression: str | None, timezone_name: str, *, after: datetime | None = None
) -> datetime:
    if not expression:
        raise CrawlTargetInvalid("schedule_cron is required")
    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise CrawlTargetInvalid(f"Unknown IANA timezone: {timezone_name}") from exc
    instant = after or datetime.now(UTC)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)
    base = instant.astimezone(timezone)
    try:
        next_local = croniter(expression, base).get_next(datetime)
    except (CroniterBadCronError, ValueError) as exc:
        raise CrawlTargetInvalid("Invalid cron expression") from exc
    return next_local.astimezone(UTC)
