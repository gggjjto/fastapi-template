from __future__ import annotations

import uuid
from typing import Any

from pydantic import Field

from app.core.schemas import CustomModel


class CrawlTaskInput(CustomModel):
    crawl_job_id: uuid.UUID
    tenant_id: uuid.UUID
    target_url_id: uuid.UUID
    target_host: str = Field(min_length=1, max_length=253)


class CrawlJobCreate(CustomModel):
    tenant_id: uuid.UUID
    target_url_id: uuid.UUID
    idempotency_key: str = Field(min_length=1, max_length=128)


class CrawlResult(CustomModel):
    data: dict[str, Any]
