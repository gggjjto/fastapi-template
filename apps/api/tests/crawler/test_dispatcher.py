from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from hatchet_sdk.exceptions import IdempotencyCollisionError

from app.crawler.persistence.repository import LeasedCrawlJob
from app.crawler.runtime import dispatcher
from app.crawler.runtime.dispatcher import dispatch_once


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class FakeRepository:
    def __init__(self) -> None:
        self.session = FakeSession()
        self.job = LeasedCrawlJob(uuid4(), uuid4(), uuid4(), "example.com", 1)
        self.dispatched: list[str] = []
        self.failures: list[str] = []

    async def lease_pending_jobs(self, *, limit: int, lease_seconds: int) -> list[LeasedCrawlJob]:
        return [self.job]

    async def mark_dispatched(self, **kwargs: Any) -> bool:
        self.dispatched.append(str(kwargs["hatchet_run_id"]))
        return True

    async def record_dispatch_failure(self, **kwargs: Any) -> None:
        self.failures.append(str(kwargs["error"]))


class FakeTask:
    def __init__(self, result: object) -> None:
        self.result = result
        self.inputs: list[object] = []

    async def aio_run(self, *, input: object, wait_for_result: bool) -> object:
        self.inputs.append(input)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeSessionContext:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *args: object) -> None:
        return None


def patch_dispatcher_runtime(monkeypatch: pytest.MonkeyPatch, *, interval: float = 1.0) -> None:
    monkeypatch.setattr(dispatcher, "Hatchet", object)
    monkeypatch.setattr(dispatcher, "create_crawl_task", lambda hatchet: object())
    monkeypatch.setattr(dispatcher, "AsyncSessionLocal", FakeSessionContext)
    monkeypatch.setattr(
        dispatcher,
        "get_settings",
        lambda: SimpleNamespace(crawler_dispatch_interval_seconds=interval),
        raising=False,
    )


async def test_dispatch_records_hatchet_run() -> None:
    repository = FakeRepository()
    count = await dispatch_once(
        repository=repository,  # type: ignore[arg-type]
        task=FakeTask(SimpleNamespace(workflow_run_id="run-1")),
    )
    assert count == 1
    assert repository.dispatched == ["run-1"]


async def test_dispatch_recovers_idempotency_collision() -> None:
    repository = FakeRepository()
    await dispatch_once(
        repository=repository,  # type: ignore[arg-type]
        task=FakeTask(IdempotencyCollisionError("existing-run")),
    )
    assert repository.dispatched == ["existing-run"]


async def test_dispatch_records_submit_failure() -> None:
    repository = FakeRepository()
    count = await dispatch_once(
        repository=repository,  # type: ignore[arg-type]
        task=FakeTask(RuntimeError("unavailable")),
    )
    assert count == 0
    assert repository.failures == ["unavailable"]


async def test_dispatcher_repeats_after_idle_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_dispatcher_runtime(monkeypatch, interval=2.5)
    dispatches = 0
    sleeps: list[float] = []

    async def dispatch(**kwargs: object) -> int:
        nonlocal dispatches
        dispatches += 1
        return 0

    async def sleep(delay: float) -> None:
        sleeps.append(delay)
        if len(sleeps) == 2:
            raise asyncio.CancelledError

    monkeypatch.setattr(dispatcher, "dispatch_once", dispatch)
    monkeypatch.setattr(dispatcher.asyncio, "sleep", sleep)

    with pytest.raises(asyncio.CancelledError):
        await dispatcher.run_dispatcher()

    assert dispatches == 2
    assert sleeps == [2.5, 2.5]


async def test_dispatcher_drains_successful_batches_without_waiting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_dispatcher_runtime(monkeypatch)
    results = iter([1, 0])
    dispatches = 0

    async def dispatch(**kwargs: object) -> int:
        nonlocal dispatches
        dispatches += 1
        return next(results)

    async def sleep(delay: float) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr(dispatcher, "dispatch_once", dispatch)
    monkeypatch.setattr(dispatcher.asyncio, "sleep", sleep)

    with pytest.raises(asyncio.CancelledError):
        await dispatcher.run_dispatcher()

    assert dispatches == 2


async def test_dispatcher_retries_after_batch_error(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_dispatcher_runtime(monkeypatch)
    dispatches = 0
    sleeps = 0

    async def dispatch(**kwargs: object) -> int:
        nonlocal dispatches
        dispatches += 1
        if dispatches == 1:
            raise RuntimeError("database unavailable")
        return 0

    async def sleep(delay: float) -> None:
        nonlocal sleeps
        sleeps += 1
        if sleeps == 2:
            raise asyncio.CancelledError

    monkeypatch.setattr(dispatcher, "dispatch_once", dispatch)
    monkeypatch.setattr(dispatcher.asyncio, "sleep", sleep)

    with pytest.raises(asyncio.CancelledError):
        await dispatcher.run_dispatcher()

    assert dispatches == 2


async def test_dispatcher_propagates_cancellation(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_dispatcher_runtime(monkeypatch)

    async def dispatch(**kwargs: object) -> int:
        raise asyncio.CancelledError

    monkeypatch.setattr(dispatcher, "dispatch_once", dispatch)

    with pytest.raises(asyncio.CancelledError):
        await dispatcher.run_dispatcher()
