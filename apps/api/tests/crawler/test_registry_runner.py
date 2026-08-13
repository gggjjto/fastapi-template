from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from hatchet_sdk.exceptions import NonRetryableException
from pydantic import ValidationError

import app.crawler.runtime.runner as runner_module
from app.crawler.domain.constants import CrawlJobStatus
from app.crawler.domain.exceptions import (
    CrawlerHTTPStatusError,
    CrawlerNetworkError,
    PermanentCrawlerError,
)
from app.crawler.domain.schemas import CrawlTaskInput
from app.crawler.runtime.registry import (
    CrawlerRegistry,
    DuplicateCrawlerError,
    UnknownCrawlerError,
)
from app.crawler.runtime.runner import _is_retryable, run_crawl_task


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


class FakeLogger:
    def __init__(self) -> None:
        self.infos: list[tuple[str, dict[str, Any]]] = []
        self.warnings: list[tuple[str, dict[str, Any]]] = []
        self.errors: list[tuple[str, dict[str, Any]]] = []

    def info(self, event: str, **kwargs: Any) -> None:
        self.infos.append((event, kwargs))

    def warning(self, event: str, **kwargs: Any) -> None:
        self.warnings.append((event, kwargs))

    def error(self, event: str, **kwargs: Any) -> None:
        self.errors.append((event, kwargs))


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
    task_input: CrawlTaskInput | None = None,
) -> RecordingRepository:
    task_input = task_input or _task_input()
    job = SimpleNamespace(
        id=task_input.crawl_job_id,
        tenant_id=task_input.tenant_id,
        status=status,
        result={"stored": True},
        hatchet_run_id=None,
    )
    target = SimpleNamespace(
        target_url_id=task_input.target_url_id,
        handler_name="html",
        target_host="example.com",
        target_url="https://example.com/secret-token",
    )
    repository = RecordingRepository(object(), job, target)
    registry = CrawlerRegistry()
    registry.register("html", handler)
    monkeypatch.setattr(runner_module, "AsyncSessionLocal", FakeSessionContext)
    monkeypatch.setattr(runner_module, "CrawlerRepository", lambda session: repository)
    monkeypatch.setattr(runner_module, "SafeAsyncCrawlerClient", FakeClient)
    monkeypatch.setattr(runner_module, "registry", registry)
    return repository


def _logged_event(logger: FakeLogger, event: str) -> dict[str, Any]:
    return next(
        fields for name, fields in logger.infos + logger.warnings + logger.errors if name == event
    )


async def test_runner_persists_success(monkeypatch: pytest.MonkeyPatch) -> None:
    repository = _install_runner_fakes(monkeypatch, _handler)
    result = await run_crawl_task(
        _task_input(),
        SimpleNamespace(attempt_number=1),  # type: ignore[arg-type]
    )
    assert result == {}
    assert repository.calls == [("running", 1), ("succeeded", {})]


async def test_runner_logs_started_job(monkeypatch: pytest.MonkeyPatch) -> None:
    logger = FakeLogger()
    task_input = _task_input()
    monkeypatch.setattr(runner_module, "logger", logger, raising=False)
    _install_runner_fakes(monkeypatch, _handler, task_input=task_input)

    await run_crawl_task(
        task_input,
        SimpleNamespace(attempt_number=1),  # type: ignore[arg-type]
    )

    assert _logged_event(logger, "crawler.execution.started") == {
        "crawl_job_id": str(task_input.crawl_job_id),
        "hatchet_run_id": None,
        "handler_name": "html",
        "target_host": "example.com",
        "attempt": 1,
    }


async def test_runner_logs_succeeded_job_without_raw_target_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = FakeLogger()
    task_input = _task_input()
    monkeypatch.setattr(runner_module, "logger", logger, raising=False)
    _install_runner_fakes(monkeypatch, _handler, task_input=task_input)

    await run_crawl_task(
        task_input,
        SimpleNamespace(attempt_number=1),  # type: ignore[arg-type]
    )

    fields = _logged_event(logger, "crawler.execution.succeeded")
    assert fields == {
        "crawl_job_id": str(task_input.crawl_job_id),
        "hatchet_run_id": None,
        "handler_name": "html",
        "target_host": "example.com",
        "attempt": 1,
        "duration_ms": fields["duration_ms"],
    }
    assert isinstance(fields["duration_ms"], float)
    assert "secret" not in str(fields)


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


async def test_runner_logs_retrying_job(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail(target: object, client: object) -> dict[str, object]:
        raise CrawlerNetworkError("timeout")

    logger = FakeLogger()
    task_input = _task_input()
    monkeypatch.setattr(runner_module, "logger", logger, raising=False)
    _install_runner_fakes(monkeypatch, fail, task_input=task_input)

    with pytest.raises(CrawlerNetworkError):
        await run_crawl_task(
            task_input,
            SimpleNamespace(attempt_number=1),  # type: ignore[arg-type]
        )

    fields = _logged_event(logger, "crawler.execution.retrying")
    assert fields == {
        "crawl_job_id": str(task_input.crawl_job_id),
        "hatchet_run_id": None,
        "handler_name": "html",
        "target_host": "example.com",
        "attempt": 1,
        "duration_ms": fields["duration_ms"],
        "error_category": "transient",
        "error_code": "CrawlerNetworkError",
    }
    assert isinstance(fields["duration_ms"], float)


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


async def test_runner_logs_failed_job(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail(target: object, client: object) -> dict[str, object]:
        raise PermanentCrawlerError("invalid")

    logger = FakeLogger()
    task_input = _task_input()
    monkeypatch.setattr(runner_module, "logger", logger, raising=False)
    _install_runner_fakes(monkeypatch, fail, task_input=task_input)

    with pytest.raises(NonRetryableException):
        await run_crawl_task(
            task_input,
            SimpleNamespace(attempt_number=1),  # type: ignore[arg-type]
        )

    fields = _logged_event(logger, "crawler.execution.failed")
    assert fields == {
        "crawl_job_id": str(task_input.crawl_job_id),
        "hatchet_run_id": None,
        "handler_name": "html",
        "target_host": "example.com",
        "attempt": 1,
        "duration_ms": fields["duration_ms"],
        "error_code": "PermanentCrawlerError",
        "error_category": "permanent",
    }
    assert isinstance(fields["duration_ms"], float)


async def test_runner_marks_exhausted_retryable_failure_as_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail(target: object, client: object) -> dict[str, object]:
        raise CrawlerNetworkError("timeout")

    repository = _install_runner_fakes(monkeypatch, fail)
    with pytest.raises(CrawlerNetworkError):
        await run_crawl_task(
            _task_input(),
            SimpleNamespace(attempt_number=3),  # type: ignore[arg-type]
        )

    assert repository.calls == [("running", 3), ("failed", "timeout")]
