from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.crawler.application.service import _next_cron_time
from app.crawler.runtime.scheduler import schedule_once


def test_next_cron_time_handles_timezone_and_dst() -> None:
    after = datetime(2026, 3, 8, 6, 30, tzinfo=UTC)
    result = _next_cron_time("0 3 * * *", "America/New_York", after=after)
    assert result == datetime(2026, 3, 8, 7, 0, tzinfo=UTC)


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class FakeRepository:
    def __init__(self) -> None:
        self.session = FakeSession()
        self.due = datetime.now(UTC)
        self.target = SimpleNamespace(
            id=uuid4(),
            tenant_id=uuid4(),
            next_run_at=self.due,
            schedule_cron="0 * * * *",
            schedule_timezone="UTC",
        )
        self.jobs: list[dict[str, object]] = []

    async def lease_due_targets(self, *, now: datetime, limit: int) -> list[object]:
        return [self.target]

    async def create_job(self, **kwargs: object) -> None:
        self.jobs.append(kwargs)


async def test_scheduler_creates_deterministic_job_and_advances_schedule() -> None:
    repository = FakeRepository()
    count = await schedule_once(repository=repository)  # type: ignore[arg-type]

    assert count == 1
    assert repository.session.commits == 1
    assert repository.jobs[0]["scheduled_for"] == repository.due
    assert repository.jobs[0]["idempotency_key"] == (
        f"schedule:{repository.target.id}:{repository.due.isoformat()}"
    )
    assert repository.target.next_run_at > repository.due
