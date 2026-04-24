"""
RedisCache 集成测试。

依赖真实 Redis（见 conftest.py / docker-compose.test.yml）。
"""

from __future__ import annotations

from redis.asyncio import Redis

from app.core.cache import RedisCache


async def test_set_and_get_roundtrip(redis_client: Redis) -> None:
    cache = RedisCache(redis_client, prefix="test", ttl=60)
    await cache.set("user:1", {"id": 1, "name": "Alice"})

    value = await cache.get("user:1")

    assert value == {"id": 1, "name": "Alice"}


async def test_get_returns_none_on_miss(redis_client: Redis) -> None:
    cache = RedisCache(redis_client, prefix="test")

    assert await cache.get("nonexistent") is None


async def test_delete_removes_value(redis_client: Redis) -> None:
    cache = RedisCache(redis_client, prefix="test")
    await cache.set("k", "v")
    assert await cache.get("k") == "v"

    await cache.delete("k")

    assert await cache.get("k") is None


async def test_delete_pattern_removes_matching_keys(redis_client: Redis) -> None:
    cache = RedisCache(redis_client, prefix="users")
    await cache.set("1", {"name": "a"})
    await cache.set("2", {"name": "b"})
    # 不应被 users:* 匹配的 key
    other = RedisCache(redis_client, prefix="posts")
    await other.set("1", {"title": "x"})

    await cache.delete_pattern("*")

    assert await cache.get("1") is None
    assert await cache.get("2") is None
    assert await other.get("1") == {"title": "x"}


async def test_delete_pattern_noop_when_no_match(redis_client: Redis) -> None:
    """保证 keys 结果为空时不会调用 delete(*[])（redis-py 会拒绝）。"""
    cache = RedisCache(redis_client, prefix="empty")

    await cache.delete_pattern("*")  # 不应抛异常


async def test_get_or_set_calls_factory_only_on_miss(redis_client: Redis) -> None:
    cache = RedisCache(redis_client, prefix="test", ttl=60)
    call_count = 0

    async def factory() -> dict[str, int]:
        nonlocal call_count
        call_count += 1
        return {"value": 42}

    first = await cache.get_or_set("key", factory)
    second = await cache.get_or_set("key", factory)
    third = await cache.get_or_set("key", factory)

    assert first == second == third == {"value": 42}
    assert call_count == 1


async def test_ttl_override(redis_client: Redis) -> None:
    cache = RedisCache(redis_client, prefix="test", ttl=60)
    await cache.set("k", "v", ttl=3600)

    # 直接查实际 TTL 应接近 3600 而不是默认 60
    actual_ttl = await redis_client.ttl("test:k")
    assert 3590 <= actual_ttl <= 3600


async def test_prefix_isolation(redis_client: Redis) -> None:
    a = RedisCache(redis_client, prefix="a")
    b = RedisCache(redis_client, prefix="b")

    await a.set("shared", 1)
    await b.set("shared", 2)

    assert await a.get("shared") == 1
    assert await b.get("shared") == 2


async def test_no_prefix(redis_client: Redis) -> None:
    cache = RedisCache(redis_client)
    await cache.set("plain", "hello")

    raw = await redis_client.get("plain")
    assert raw == '"hello"'
