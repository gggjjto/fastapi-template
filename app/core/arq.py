from __future__ import annotations

from typing import Annotated

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from fastapi import Depends

from app.core.config import get_settings

settings = get_settings()

_pool: ArqRedis | None = None


async def init_arq() -> None:
    """在 app lifespan 启动时调用，初始化 Arq 任务队列连接池。"""
    global _pool
    _pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))  # type: ignore[arg-type]


async def close_arq() -> None:
    """在 app lifespan 关闭时调用，释放 Arq 连接池。"""
    global _pool
    if _pool:
        await _pool.aclose()
        _pool = None


async def get_arq() -> ArqRedis:
    """FastAPI 依赖函数，返回全局 Arq 连接池实例。"""
    if _pool is None:
        raise RuntimeError("Arq 未初始化 — 请设置 APP_REDIS_URL 并重启服务")
    return _pool


# 依赖注入别名，在接口函数中使用：queue: ArqPool
ArqPool = Annotated[ArqRedis, Depends(get_arq)]
