"""Hatchet Cloud worker entry point.

Start locally with ``uv run python -m app.worker``.
"""

from __future__ import annotations

import structlog
from hatchet_sdk import Context, Hatchet
from hatchet_sdk.worker.worker import Worker
from pydantic import BaseModel

from app.crawler.registry import discover_handlers
from app.crawler.runner import create_crawl_task

logger = structlog.get_logger(__name__)
hatchet = Hatchet()


class ExampleTaskInput(BaseModel):
    message: str


class ExampleTaskOutput(BaseModel):
    transformed_message: str


async def run_example_task(task_input: ExampleTaskInput) -> ExampleTaskOutput:
    """Pure example logic that can be tested without a Hatchet worker."""
    return ExampleTaskOutput(transformed_message=task_input.message.upper())


async def _example_task(task_input: ExampleTaskInput, _context: Context) -> ExampleTaskOutput:
    logger.info("worker.example_task")
    return await run_example_task(task_input)


example_task = hatchet.task(
    name="example-task",
    input_validator=ExampleTaskInput,
)(_example_task)

crawl_task = create_crawl_task(hatchet)


def create_worker() -> Worker:
    discover_handlers()
    return hatchet.worker(
        "fastapi-template-worker",
        slots=10,
        workflows=[example_task, crawl_task],
    )


def main() -> None:
    create_worker().start()


if __name__ == "__main__":
    main()
