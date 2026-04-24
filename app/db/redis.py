from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from app.core.config import get_settings

settings = get_settings()

_redis: Redis | None = None


async def init_redis() -> None:
    """在 app lifespan 启动时调用，初始化 Redis 连接池。"""
    global _redis
    _redis = Redis.from_url(settings.redis_url, decode_responses=True)  # type: ignore[arg-type]


async def close_redis() -> None:
    """在 app lifespan 关闭时调用，释放 Redis 连接。"""
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


async def get_redis() -> Redis:
    """FastAPI 依赖函数，返回全局 Redis 客户端实例。"""
    if _redis is None:
        raise RuntimeError("Redis 未初始化 — 请设置 APP_REDIS_URL 并重启服务")
    return _redis


# 依赖注入别名，在接口函数中使用：redis: RedisClient
RedisClient = Annotated[Redis, Depends(get_redis)]
