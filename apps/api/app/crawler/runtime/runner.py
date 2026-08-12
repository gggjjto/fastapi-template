from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

from hatchet_sdk import Context, Hatchet
from hatchet_sdk.exceptions import NonRetryableException
from hatchet_sdk.types.concurrency import ConcurrencyExpression, ConcurrencyLimitStrategy
from hatchet_sdk.types.idempotency import TTLBasedIdempotencyConfig
from hatchet_sdk.types.rate_limit import RateLimit, RateLimitDuration
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


def create_crawl_task(hatchet: Hatchet) -> Any:
    return hatchet.task(
        name="crawler.crawl",
        input_validator=CrawlTaskInput,
        retries=2,
        backoff_factor=2,
        backoff_max_seconds=300,
        execution_timeout=timedelta(minutes=5),
        concurrency=[
            ConcurrencyExpression(
                expression="input.target_host",
                max_runs=2,
                limit_strategy=ConcurrencyLimitStrategy.GROUP_ROUND_ROBIN,
            )
        ],
        rate_limits=[
            RateLimit(
                dynamic_key="input.target_host",
                units=1,
                limit=1,
                duration=RateLimitDuration.SECOND,
            )
        ],
        idempotency=TTLBasedIdempotencyConfig(
            key_expression="input.crawl_job_id",
            ttl=timedelta(days=30),
        ),
    )(_crawl_task)


async def run_crawl_task(task_input: CrawlTaskInput, context: Context) -> dict[str, object] | None:
    async with AsyncSessionLocal() as session:
        repository = CrawlerRepository(session)
        loaded = await repository.load_for_execution(
            job_id=task_input.crawl_job_id,
            tenant_id=task_input.tenant_id,
            target_url_id=task_input.target_url_id,
        )
        if loaded is None:
            raise NonRetryableException("crawler job or target not found")
        job, target = loaded
        if job.status in CrawlJobStatus.terminal():
            return job.result

        attempt_count = int(context.attempt_number)
        await repository.mark_running(job, attempt_count=attempt_count)
        try:
            if task_input.target_host != target.target_host:
                raise PermanentCrawlerError("crawler task host does not match the stored target")
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
                raise
            category = CrawlErrorCategory.TRANSIENT if retryable else _error_category(exc)
            await repository.mark_failed(job, error=exc, category=category)
            if retryable:
                raise
            raise NonRetryableException(str(exc)) from exc

        await repository.mark_succeeded(job, result=result)
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
