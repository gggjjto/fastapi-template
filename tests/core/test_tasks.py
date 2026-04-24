"""
后台任务 / Arq 集成测试。

验证 worker 任务函数逻辑，以及 app lifespan 能正确初始化 Arq pool 并支持入队。
"""

from __future__ import annotations

from httpx import AsyncClient

from app.core.arq import get_arq
from app.worker import example_task


async def test_example_task_returns_expected_message() -> None:
    ctx = {"job_id": "job-123"}

    result = await example_task(ctx, "hello")

    assert "hello" in result


async def test_arq_pool_initialized_in_lifespan(client: AsyncClient) -> None:
    """
    只要 client fixture 走过 lifespan，`get_arq()` 就应返回 pool 而不抛异常。
    """
    pool = await get_arq()

    assert pool is not None
    # 入队一个任务（不启动 worker，仅验证连接可用 + 协议正常）
    job = await pool.enqueue_job("example_task", "ping")
    assert job is not None

    job_info = await job.info()
    assert job_info is not None
    assert job_info.function == "example_task"
