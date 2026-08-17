from __future__ import annotations

from app.core.exceptions import BadRequestError, ConflictError, DomainError, NotFoundError
from app.crawler.domain.constants import ErrorCode


class CrawlJobConflict(ConflictError):
    def __init__(self, message: str = "Crawl job idempotency key is already used") -> None:
        super().__init__(message, code=ErrorCode.CRAWL_JOB_CONFLICT)


class CrawlTargetNotFound(NotFoundError):
    def __init__(self) -> None:
        super().__init__("Crawl target not found", code=ErrorCode.CRAWL_TARGET_NOT_FOUND)


class CrawlJobNotFound(NotFoundError):
    def __init__(self) -> None:
        super().__init__("Crawl job not found", code=ErrorCode.CRAWL_JOB_NOT_FOUND)


class CrawlJobInvalidState(ConflictError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code=ErrorCode.CRAWL_JOB_INVALID_STATE)


class CrawlCancellationUnavailable(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "Crawler cancellation service is unavailable",
            code=ErrorCode.CRAWL_CANCELLATION_UNAVAILABLE,
            status_code=503,
        )


class CrawlHandlerNotFound(BadRequestError):
    def __init__(self, handler_name: str) -> None:
        super().__init__(
            f"Unknown crawler handler: {handler_name}", code=ErrorCode.CRAWL_HANDLER_NOT_FOUND
        )


class CrawlTargetInvalid(BadRequestError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


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
