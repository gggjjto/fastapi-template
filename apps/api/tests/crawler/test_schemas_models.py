from __future__ import annotations

from typing import cast
from uuid import uuid4

from sqlalchemy import Table, UniqueConstraint

from app.crawler.domain.constants import CrawlJobStatus
from app.crawler.domain.models import CrawlJob, CrawlTarget
from app.crawler.domain.schemas import CrawlTaskInput


def _unique_columns(table: Table) -> set[tuple[str, ...]]:
    return {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def test_crawl_task_input_contains_only_routing_metadata() -> None:
    payload = CrawlTaskInput(
        crawl_job_id=uuid4(),
        tenant_id=uuid4(),
        target_url_id=uuid4(),
        target_host="example.com",
    )
    assert set(payload.model_dump()) == {
        "crawl_job_id",
        "tenant_id",
        "target_url_id",
        "target_host",
    }


def test_tenant_scoped_unique_constraints() -> None:
    assert ("tenant_id", "target_url_id") in _unique_columns(cast(Table, CrawlTarget.__table__))
    assert ("tenant_id", "idempotency_key") in _unique_columns(cast(Table, CrawlJob.__table__))


def test_terminal_job_states() -> None:
    assert CrawlJobStatus.terminal() == {CrawlJobStatus.SUCCEEDED, CrawlJobStatus.FAILED}


def test_finished_at_has_diagnostics_index() -> None:
    table = cast(Table, CrawlJob.__table__)
    assert "ix_crawl_jobs_finished_at" in {index.name for index in table.indexes}
