from __future__ import annotations

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawler.domain.exceptions import CrawlJobConflict, CrawlTargetNotFound
from app.crawler.domain.models import CrawlJob
from app.crawler.domain.schemas import CrawlJobCreate
from app.crawler.persistence.repository import CrawlerRepository

logger = structlog.get_logger(__name__)


class CrawlerService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = CrawlerRepository(session)

    async def create_or_reuse_job(self, payload: CrawlJobCreate) -> CrawlJob:
        existing = await self.repository.get_job_by_idempotency_key(
            tenant_id=payload.tenant_id,
            idempotency_key=payload.idempotency_key,
        )
        if existing is not None:
            return existing

        target = await self.repository.get_target(
            tenant_id=payload.tenant_id,
            target_url_id=payload.target_url_id,
        )
        if target is None or not target.enabled:
            raise CrawlTargetNotFound()

        try:
            job = await self.repository.create_job(
                tenant_id=payload.tenant_id,
                crawl_target_id=target.id,
                idempotency_key=payload.idempotency_key,
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
                tenant_id=payload.tenant_id,
                idempotency_key=payload.idempotency_key,
            )
            if existing is not None:
                return existing
            raise CrawlJobConflict() from exc
