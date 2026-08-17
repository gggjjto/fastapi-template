from __future__ import annotations

from enum import StrEnum


class CrawlJobStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    RETRYING = "retrying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def terminal(cls) -> set[CrawlJobStatus]:
        return {cls.SUCCEEDED, cls.FAILED, cls.CANCELLED}


class CrawlDispatchState(StrEnum):
    PENDING = "pending"
    LEASED = "leased"
    DISPATCHED = "dispatched"
    FAILED = "failed"


class CrawlErrorCategory(StrEnum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    POLICY = "policy"
    UNEXPECTED = "unexpected"


LEASE_SECONDS = 60
MAX_DISPATCH_ATTEMPTS = 5
MAX_EXECUTION_ATTEMPTS = 3


class ErrorCode:
    CRAWL_JOB_CONFLICT = "CRAWL_JOB_CONFLICT"
    CRAWL_TARGET_NOT_FOUND = "CRAWL_TARGET_NOT_FOUND"
    CRAWL_JOB_NOT_FOUND = "CRAWL_JOB_NOT_FOUND"
    CRAWL_JOB_INVALID_STATE = "CRAWL_JOB_INVALID_STATE"
    CRAWL_CANCELLATION_UNAVAILABLE = "CRAWL_CANCELLATION_UNAVAILABLE"
    CRAWL_HANDLER_NOT_FOUND = "CRAWL_HANDLER_NOT_FOUND"
