from __future__ import annotations

import json
import time
from datetime import timedelta
from typing import Any

import structlog
from hatchet_sdk import Context, Hatchet
from hatchet_sdk.exceptions import NonRetryableException
from hatchet_sdk.types.idempotency import TTLBasedIdempotencyConfig
from pydantic import ValidationError

from app.crawler.domain.constants import (
    MAX_EXECUTION_ATTEMPTS,
    CrawlErrorCategory,
    CrawlJobStatus,
)
from app.crawler.domain.exceptions import PermanentCrawlerError
from app.crawler.domain.schemas import CrawlTaskInput
from app.crawler.network.http_client import SafeAsyncCrawlerClient
from app.crawler.persistence.repository import CrawlerRepository
from app.crawler.runtime.registry import registry
from app.db.session import AsyncSessionLocal

logger = structlog.get_logger(__name__)


def create_crawl_task(hatchet: Hatchet) -> Any:
    return hatchet.task(
        name="crawler.crawl",
        input_validator=CrawlTaskInput,
        retries=2,
        backoff_factor=2,
        backoff_max_seconds=300,
        execution_timeout=timedelta(minutes=5),
        idempotency=TTLBasedIdempotencyConfig(
            key_expression="input.crawl_job_id",
            ttl=timedelta(days=30),
        ),
    )(_crawl_task)


async def run_crawl_task(task_input: CrawlTaskInput, context: Context) -> dict[str, object] | None:
    async with AsyncSessionLocal() as session:
        repository = CrawlerRepository(session)
        loaded = await repository.load_for_execution(job_id=task_input.crawl_job_id)
        if loaded is None:
            raise NonRetryableException("crawler job or target not found")
        job, target = loaded
        if job.status in CrawlJobStatus.terminal():
            return job.result

        attempt_count = int(context.attempt_number)
        start = time.perf_counter()
        if not await repository.mark_running(job, attempt_count=attempt_count):
            return job.result
        log_context = {
            "crawl_job_id": str(job.id),
            "hatchet_run_id": job.hatchet_run_id,
            "handler_name": target.handler_name,
            "target_host": target.target_host,
            "attempt": attempt_count,
        }
        logger.info("crawler.execution.started", **log_context)
        try:
            handler = registry.get(target.handler_name)
            async with SafeAsyncCrawlerClient() as client:
                result = await handler(target, client)
            try:
                json.dumps(result)
            except (TypeError, ValueError) as exc:
                raise PermanentCrawlerError("crawler result must be JSON serializable") from exc
        except Exception as exc:
            retryable = _is_retryable(exc)
            if retryable and attempt_count < MAX_EXECUTION_ATTEMPTS:
                await repository.mark_retrying(job, error=exc)
                logger.warning(
                    "crawler.execution.retrying",
                    **log_context,
                    duration_ms=round((time.perf_counter() - start) * 1000, 2),
                    error_category=CrawlErrorCategory.TRANSIENT,
                    error_code=exc.__class__.__name__,
                )
                raise
            category = CrawlErrorCategory.TRANSIENT if retryable else _error_category(exc)
            await repository.mark_failed(job, error=exc, category=category)
            logger.error(
                "crawler.execution.failed",
                **log_context,
                duration_ms=round((time.perf_counter() - start) * 1000, 2),
                error_category=category,
                error_code=exc.__class__.__name__,
            )
            if retryable:
                raise
            raise NonRetryableException(str(exc)) from exc

        await repository.mark_succeeded(job, result=result)
        logger.info(
            "crawler.execution.succeeded",
            **log_context,
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )
        return result


async def _crawl_task(task_input: CrawlTaskInput, context: Context) -> dict[str, object] | None:
    return await run_crawl_task(task_input, context)


def _is_retryable(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        return status_code in {408, 429} or status_code >= 500
    if getattr(exc, "retryable", False):
        return True
    return not isinstance(exc, (PermanentCrawlerError, ValidationError))


def _error_category(exc: Exception) -> CrawlErrorCategory:
    if getattr(exc, "policy_error", False):
        return CrawlErrorCategory.POLICY
    return CrawlErrorCategory.PERMANENT
