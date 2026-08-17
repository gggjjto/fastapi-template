from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field, field_validator, model_validator

from app.core.schemas import CustomModel
from app.crawler.domain.constants import CrawlDispatchState, CrawlJobStatus


class CrawlTaskInput(CustomModel):
    crawl_job_id: uuid.UUID


class CrawlTargetCreate(CustomModel):
    name: str = Field(min_length=1, max_length=128)
    target_url: str = Field(min_length=1, max_length=2048)
    handler_name: str = Field(default="http_snapshot", min_length=1, max_length=128)
    enabled: bool = True
    schedule_cron: str | None = Field(default=None, max_length=128)
    schedule_timezone: str = Field(default="UTC", min_length=1, max_length=64)
    schedule_enabled: bool = False

    @model_validator(mode="after")
    def schedule_requires_cron(self) -> CrawlTargetCreate:
        if self.schedule_enabled and not self.schedule_cron:
            raise ValueError("schedule_cron is required when scheduling is enabled")
        return self


class CrawlTargetUpdate(CustomModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    target_url: str | None = Field(default=None, min_length=1, max_length=2048)
    handler_name: str | None = Field(default=None, min_length=1, max_length=128)
    enabled: bool | None = None
    schedule_cron: str | None = Field(default=None, max_length=128)
    schedule_timezone: str | None = Field(default=None, min_length=1, max_length=64)
    schedule_enabled: bool | None = None


class CrawlTargetRead(CustomModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    target_url: str
    target_host: str
    handler_name: str
    enabled: bool
    schedule_cron: str | None
    schedule_timezone: str
    schedule_enabled: bool
    next_run_at: datetime | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CrawlJobCreate(CustomModel):
    target_id: uuid.UUID
    idempotency_key: str = Field(min_length=1, max_length=128)


class CrawlRunCreate(CustomModel):
    idempotency_key: str = Field(min_length=1, max_length=128)


class CrawlJobRead(CustomModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    crawl_target_id: uuid.UUID
    idempotency_key: str
    status: CrawlJobStatus
    dispatch_state: CrawlDispatchState
    dispatch_attempts: int
    hatchet_run_id: str | None
    attempt_count: int
    max_attempts: int
    error_category: str | None
    error_code: str | None
    error_message: str | None
    result: dict[str, Any] | None
    scheduled_for: datetime | None
    retry_of_job_id: uuid.UUID | None
    cancel_requested_at: datetime | None
    dispatched_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CrawlHandlerRead(CustomModel):
    name: str


class CrawlMetricDurations(CustomModel):
    p50_ms: float | None
    p95_ms: float | None


class CrawlMetrics(CustomModel):
    from_at: datetime
    to_at: datetime
    total: int
    errors: int
    by_status: dict[str, int]
    dispatch: CrawlMetricDurations
    queue: CrawlMetricDurations
    run: CrawlMetricDurations
    total_duration: CrawlMetricDurations


class CrawlResult(CustomModel):
    final_url: str
    status_code: int
    content_type: str | None
    content_length: int = Field(ge=0)
    sha256: str
    body: str | None = None
    truncated: bool = False

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if len(value) != 64:
            raise ValueError("sha256 must be a hexadecimal SHA-256 digest")
        int(value, 16)
        return value
