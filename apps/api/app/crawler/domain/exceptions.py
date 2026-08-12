from __future__ import annotations

from app.core.exceptions import ConflictError, NotFoundError
from app.crawler.domain.constants import ErrorCode


class CrawlJobConflict(ConflictError):
    def __init__(self, message: str = "Crawl job idempotency key is already used") -> None:
        super().__init__(message, code=ErrorCode.CRAWL_JOB_CONFLICT)


class CrawlTargetNotFound(NotFoundError):
    def __init__(self) -> None:
        super().__init__("Crawl target not found", code=ErrorCode.CRAWL_TARGET_NOT_FOUND)


class CrawlerError(Exception):
    retryable = False


class RetryableCrawlerError(CrawlerError):
    retryable = True


class PermanentCrawlerError(CrawlerError):
    pass


class CrawlerNetworkError(RetryableCrawlerError):
    pass


class CrawlerUnsafeHostError(PermanentCrawlerError):
    policy_error = True


class CrawlerRedirectError(PermanentCrawlerError):
    policy_error = True


class CrawlerBodyTooLargeError(PermanentCrawlerError):
    policy_error = True


class CrawlerHTTPStatusError(CrawlerError):
    def __init__(self, status_code: int, url: str) -> None:
        super().__init__(f"HTTP {status_code} for {url}")
        self.status_code = status_code
        self.retryable = status_code in {408, 429} or status_code >= 500
