from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from hatchet_sdk.exceptions import IdempotencyCollisionError

from app.crawler.persistence.repository import LeasedCrawlJob
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
