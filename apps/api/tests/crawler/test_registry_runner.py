from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from hatchet_sdk.exceptions import NonRetryableException
from pydantic import ValidationError

import app.crawler.runner as runner_module
from app.crawler.constants import CrawlJobStatus
from app.crawler.exceptions import (
    CrawlerHTTPStatusError,
    CrawlerNetworkError,
    PermanentCrawlerError,
)
from app.crawler.registry import CrawlerRegistry, DuplicateCrawlerError, UnknownCrawlerError
from app.crawler.runner import _is_retryable, run_crawl_task
from app.crawler.schemas import CrawlTaskInput


async def _handler(target: Any, client: Any) -> dict[str, object]:
    return {}


def test_registry_registers_and_rejects_duplicates() -> None:
    registry = CrawlerRegistry()
    registry.register("html", _handler)
    assert registry.get("html") is _handler
    with pytest.raises(DuplicateCrawlerError):
        registry.register("html", _handler)
    with pytest.raises(UnknownCrawlerError):
        registry.get("missing")


def test_retry_policy_classifies_http_and_validation_failures() -> None:
    assert _is_retryable(CrawlerHTTPStatusError(408, "https://example.com"))
    assert _is_retryable(CrawlerHTTPStatusError(500, "https://example.com"))
    assert not _is_retryable(CrawlerHTTPStatusError(404, "https://example.com"))
    assert not _is_retryable(PermanentCrawlerError("bad document"))
    validation_error = ValidationError.from_exception_data("test", [])
    assert not _is_retryable(validation_error)


class FakeSessionContext:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *args: object) -> None:
        return None


class FakeClient:
    async def __aenter__(self) -> FakeClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class RecordingRepository:
    def __init__(self, session: object, job: object, target: object) -> None:
        self.job = job
        self.target = target
        self.calls: list[tuple[str, object]] = []

    async def load_for_execution(self, **kwargs: object) -> tuple[object, object]:
        return self.job, self.target

    async def mark_running(self, job: object, *, attempt_count: int) -> None:
        self.calls.append(("running", attempt_count))

    async def mark_retrying(self, job: object, *, error: Exception) -> None:
        self.calls.append(("retrying", str(error)))

    async def mark_succeeded(self, job: object, *, result: dict[str, object]) -> None:
        self.calls.append(("succeeded", result))

    async def mark_failed(self, job: object, *, error: Exception, category: object) -> None:
        self.calls.append(("failed", str(error)))


def _task_input() -> CrawlTaskInput:
    return CrawlTaskInput(
        crawl_job_id=uuid4(),
        tenant_id=uuid4(),
        target_url_id=uuid4(),
        target_host="example.com",
    )


def _install_runner_fakes(
    monkeypatch: pytest.MonkeyPatch,
    handler: Any,
    *,
    status: CrawlJobStatus = CrawlJobStatus.QUEUED,
) -> RecordingRepository:
    job = SimpleNamespace(status=status, result={"stored": True})
    target = SimpleNamespace(handler_name="html", target_host="example.com")
    repository = RecordingRepository(object(), job, target)
    registry = CrawlerRegistry()
    registry.register("html", handler)
    monkeypatch.setattr(runner_module, "AsyncSessionLocal", FakeSessionContext)
    monkeypatch.setattr(runner_module, "CrawlerRepository", lambda session: repository)
    monkeypatch.setattr(runner_module, "SafeAsyncCrawlerClient", FakeClient)
    monkeypatch.setattr(runner_module, "registry", registry)
    return repository


async def test_runner_persists_success(monkeypatch: pytest.MonkeyPatch) -> None:
    repository = _install_runner_fakes(monkeypatch, _handler)
    result = await run_crawl_task(
        _task_input(),
        SimpleNamespace(attempt_number=1),  # type: ignore[arg-type]
    )
    assert result == {}
    assert repository.calls == [("running", 1), ("succeeded", {})]


async def test_runner_short_circuits_terminal_job(monkeypatch: pytest.MonkeyPatch) -> None:
    repository = _install_runner_fakes(monkeypatch, _handler, status=CrawlJobStatus.SUCCEEDED)
    result = await run_crawl_task(
        _task_input(),
        SimpleNamespace(attempt_number=2),  # type: ignore[arg-type]
    )
    assert result == {"stored": True}
    assert repository.calls == []


async def test_runner_records_retryable_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail(target: object, client: object) -> dict[str, object]:
        raise CrawlerNetworkError("timeout")

    repository = _install_runner_fakes(monkeypatch, fail)
    with pytest.raises(CrawlerNetworkError):
        await run_crawl_task(
            _task_input(),
            SimpleNamespace(attempt_number=1),  # type: ignore[arg-type]
        )
    assert repository.calls == [("running", 1), ("retrying", "timeout")]


async def test_runner_stops_retrying_permanent_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail(target: object, client: object) -> dict[str, object]:
        raise PermanentCrawlerError("invalid")

    repository = _install_runner_fakes(monkeypatch, fail)
    with pytest.raises(NonRetryableException):
        await run_crawl_task(
            _task_input(),
            SimpleNamespace(attempt_number=1),  # type: ignore[arg-type]
        )
    assert repository.calls == [("running", 1), ("failed", "invalid")]
