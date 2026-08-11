"""
后台任务 / Hatchet Worker 测试。

验证任务纯逻辑、Pydantic 输入输出，以及 worker 注册合约。
"""

from __future__ import annotations

import importlib
from typing import Any

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    return None


def _load_worker_module(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv(
        "HATCHET_CLIENT_TOKEN",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiJ0ZW5hbnQtdGVzdCIsInNlcnZlcl91cmwiOiJodHRwOi8vbG9j"
        "YWxob3N0Ojg4ODgiLCJncnBjX2Jyb2FkY2FzdF9hZGRyZXNzIjoibG9j"
        "YWxob3N0OjcwNzAifQ."
        "signature",
    )
    import app.worker as worker_module

    return importlib.reload(worker_module)


def test_example_task_input_requires_message(monkeypatch: pytest.MonkeyPatch) -> None:
    worker_module = _load_worker_module(monkeypatch)

    with pytest.raises(ValidationError):
        worker_module.ExampleTaskInput()


def test_example_task_input_serializes_message(monkeypatch: pytest.MonkeyPatch) -> None:
    worker_module = _load_worker_module(monkeypatch)

    task_input = worker_module.ExampleTaskInput(message="hello")

    assert task_input.model_dump() == {"message": "hello"}


async def test_run_example_task_returns_transformed_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker_module = _load_worker_module(monkeypatch)

    result = await worker_module.run_example_task(
        worker_module.ExampleTaskInput(message="hello"),
    )

    assert result == worker_module.ExampleTaskOutput(transformed_message="HELLO")


def test_create_worker_registers_example_task_with_expected_capacity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker_module = _load_worker_module(monkeypatch)
    created_worker = object()
    calls: list[dict[str, Any]] = []

    class RecordingHatchet:
        def worker(
            self,
            name: str,
            *,
            slots: int | None = None,
            workflows: list[Any] | None = None,
            **kwargs: Any,
        ) -> object:
            calls.append(
                {
                    "name": name,
                    "slots": slots,
                    "workflows": workflows,
                    "kwargs": kwargs,
                }
            )
            return created_worker

    monkeypatch.setattr(worker_module, "hatchet", RecordingHatchet())

    result = worker_module.create_worker()

    assert result is created_worker
    assert calls == [
        {
            "name": "fastapi-template-worker",
            "slots": 10,
            "workflows": [worker_module.example_task, worker_module.crawl_task],
            "kwargs": {},
        }
    ]


def test_crawl_task_uses_expected_hatchet_policy() -> None:
    from app.crawler.runner import create_crawl_task
    from app.crawler.schemas import CrawlTaskInput

    calls: list[dict[str, Any]] = []

    class RecordingHatchet:
        def task(self, **kwargs: Any) -> Any:
            calls.append(kwargs)

            def decorator(func: Any) -> Any:
                return func

            return decorator

    create_crawl_task(RecordingHatchet())  # type: ignore[arg-type]

    assert calls[0]["name"] == "crawler.crawl"
    assert calls[0]["input_validator"] is CrawlTaskInput
    assert calls[0]["retries"] == 2
    assert calls[0]["backoff_factor"] == 2
    assert calls[0]["backoff_max_seconds"] == 300


async def test_fastapi_starts_without_hatchet_client_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HATCHET_CLIENT_TOKEN", raising=False)

    import app.auth.seed as seed_module
    import app.db.session as session_module
    import app.main as main_module

    class FakeSession:
        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, *exc_info: object) -> None:
            return None

    async def ensure_default_rbac(_: object) -> None:
        return None

    async def close_db() -> None:
        return None

    monkeypatch.setattr(main_module.settings, "db_create_tables_on_startup", False)
    monkeypatch.setattr(main_module.settings, "redis_url", None)
    monkeypatch.setattr(seed_module, "ensure_default_rbac", ensure_default_rbac)
    monkeypatch.setattr(session_module, "AsyncSessionLocal", FakeSession)
    monkeypatch.setattr(main_module, "close_db", close_db)

    async with LifespanManager(main_module.app) as manager:
        async with AsyncClient(
            transport=ASGITransport(app=manager.app),
            base_url="http://test",
        ) as client:
            response = await client.get("/")

    assert response.status_code == 200
