from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from redis.asyncio import Redis

T = TypeVar("T")


class RedisCache:
    """
    基于 Redis 的 JSON 缓存封装。

    在 repository 或 service 中典型用法：

        cache = RedisCache(redis, prefix="users", ttl=300)

        async def get_user(user_id: str) -> dict:
            return await cache.get_or_set(
                key=user_id,
                factory=lambda: self._fetch_from_db(user_id),
            )

    写操作（新建/修改/删除）后，调用 cache.delete(key) 主动失效对应缓存。
    """

    def __init__(self, redis: Redis, prefix: str = "", ttl: int = 300) -> None:
        self._redis = redis
        self._prefix = prefix
        self._ttl = ttl

    # ── 基础操作 ──────────────────────────────────────────────────────────────

    def _key(self, key: str) -> str:
        return f"{self._prefix}:{key}" if self._prefix else key

    async def get(self, key: str) -> Any | None:
        raw = await self._redis.get(self._key(key))
        return json.loads(raw) if raw is not None else None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        await self._redis.setex(
            self._key(key),
            ttl if ttl is not None else self._ttl,
            json.dumps(value, default=str),
        )

    async def delete(self, key: str) -> None:
        await self._redis.delete(self._key(key))

    async def delete_pattern(self, pattern: str) -> None:
        """删除匹配 glob 模式的所有 key（key 数量大时谨慎使用）。"""
        keys = await self._redis.keys(self._key(pattern))
        if keys:
            await self._redis.delete(*keys)

    # ── 读穿透（Read-through）────────────────────────────────────────────────

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[T]],
        ttl: int | None = None,
    ) -> T:
        """缓存命中则直接返回；未命中则调用 factory 计算并写入缓存后返回。"""
        cached = await self.get(key)
        if cached is not None:
            return cached  # type: ignore[return-value]
        value = await factory()
        await self.set(key, value, ttl)
        return value
