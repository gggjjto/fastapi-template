"""
Arq 后台任务 Worker。

本地启动 Worker：
    uv run arq app.worker.WorkerSettings

生产环境中作为独立进程（或独立容器）与 API 服务并行运行。
每个任务函数的第一个参数 ctx 由 Arq 注入，包含 redis、job_id 等信息。
"""

from __future__ import annotations

from typing import ClassVar

import structlog
from arq.connections import RedisSettings

from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


# ── 任务定义 ──────────────────────────────────────────────────────────────────
# 在此添加任务函数，并在 WorkerSettings.functions 中注册。
# 在路由或服务中入队：await queue.enqueue_job("任务函数名", 参数...)


async def example_task(ctx: dict, message: str) -> str:
    """示例任务，替换为真实业务逻辑。"""
    logger.info("worker.example_task", message=message, job_id=ctx["job_id"])
    return f"已处理：{message}"


# ── Worker 配置 ───────────────────────────────────────────────────────────────


class WorkerSettings:
    functions: ClassVar = [example_task]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)  # type: ignore[arg-type]
    max_jobs = 10
    job_timeout = 300  # 单个任务超时时间（秒），超时后标记为失败
    keep_result = 3_600  # 任务结果在 Redis 中保留时间（秒）
    retry_jobs = True
    max_tries = 3
