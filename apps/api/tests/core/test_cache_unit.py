from __future__ import annotations

from collections.abc import AsyncIterator

from app.core.cache import RedisCache


class _FakeRedis:
    def __init__(self, keys: list[str]) -> None:
        self.keys = keys
        self.deleted_batches: list[tuple[str, ...]] = []

    async def scan_iter(
        self, match: str | None = None, count: int | None = None
    ) -> AsyncIterator[str]:
        for key in self.keys:
            yield key

    async def delete(self, *keys: str) -> None:
        self.deleted_batches.append(keys)


async def test_delete_pattern_deletes_scan_results_in_batches() -> None:
    redis = _FakeRedis(["cache:1", "cache:2", "cache:3"])
    cache = RedisCache(redis, prefix="cache")  # type: ignore[arg-type]

    await cache.delete_pattern("*", batch_size=2)

    assert redis.deleted_batches == [("cache:1", "cache:2"), ("cache:3",)]
