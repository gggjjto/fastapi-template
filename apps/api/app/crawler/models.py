from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.crawler.constants import MAX_EXECUTION_ATTEMPTS, CrawlDispatchState, CrawlJobStatus
from app.db.base import Base

ResultJson = JSON().with_variant(JSONB, "postgresql")


class CrawlTarget(Base):
    __tablename__ = "crawl_targets"
    __table_args__ = (
        UniqueConstraint("tenant_id", "target_url_id", name="uq_crawl_targets_tenant_target_url"),
        CheckConstraint("target_url <> ''", name="target_url_not_empty"),
        CheckConstraint("target_host <> ''", name="target_host_not_empty"),
        CheckConstraint("handler_name <> ''", name="handler_name_not_empty"),
        Index("ix_crawl_targets_tenant_id", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    target_url_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    target_host: Mapped[str] = mapped_column(String(253), nullable=False)
    handler_name: Mapped[str] = mapped_column(String(128), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_crawl_jobs_tenant_idempotency"),
        CheckConstraint(
            "status IN ('pending', 'queued', 'running', 'retrying', 'succeeded', 'failed')",
            name="status_valid",
        ),
        CheckConstraint(
            "dispatch_state IN ('pending', 'leased', 'dispatched', 'failed')",
            name="dispatch_state_valid",
        ),
        CheckConstraint("dispatch_attempts >= 0", name="dispatch_attempts_non_negative"),
        CheckConstraint("attempt_count >= 0", name="attempt_count_non_negative"),
        Index("ix_crawl_jobs_tenant_id", "tenant_id"),
        Index(
            "ix_crawl_jobs_dispatch", "dispatch_state", "next_dispatch_at", "dispatch_lease_until"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    crawl_target_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("crawl_targets.id", ondelete="CASCADE"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=CrawlJobStatus.PENDING, nullable=False)
    dispatch_state: Mapped[str] = mapped_column(
        String(32), default=CrawlDispatchState.PENDING, nullable=False
    )
    dispatch_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dispatch_lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_dispatch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    hatchet_run_id: Mapped[str | None] = mapped_column(String(255))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(
        Integer, default=MAX_EXECUTION_ATTEMPTS, nullable=False
    )
    error_category: Mapped[str | None] = mapped_column(String(32))
    error_code: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    result: Mapped[dict[str, Any] | None] = mapped_column(ResultJson)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
