from __future__ import annotations

from uuid import uuid4

from app.crawler.domain.constants import CrawlJobStatus
from app.crawler.domain.models import CrawlJob, CrawlTarget
from app.crawler.domain.schemas import CrawlTaskInput


def _unique_columns(model: type[object]) -> set[tuple[str, ...]]:
    return {
        tuple(column.name for column in constraint.columns)
        for constraint in model.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
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
    assert ("tenant_id", "target_url_id") in _unique_columns(CrawlTarget)
    assert ("tenant_id", "idempotency_key") in _unique_columns(CrawlJob)


def test_terminal_job_states() -> None:
    assert CrawlJobStatus.terminal() == {CrawlJobStatus.SUCCEEDED, CrawlJobStatus.FAILED}
