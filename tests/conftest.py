"""
全局测试夹具。

本套测试是**集成测试**，默认依赖真实的 PostgreSQL 和 Redis。

本地启动依赖：
    make test-up        # docker compose -f docker-compose.test.yml up -d
    make test           # 运行测试
    make test-down      # 停止并清理容器

可通过环境变量覆盖默认连接（CI / 自定义主机端口等）：
    APP_DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
    APP_REDIS_URL=redis://host:6379/0
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

# 必须在 import app 之前设置，否则 Settings 单例会用错默认值
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault(
    "APP_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5433/app_test",
)
os.environ.setdefault("APP_REDIS_URL", "redis://localhost:6380/0")
os.environ.setdefault("APP_DB_CREATE_TABLES_ON_STARTUP", "false")
os.environ.setdefault(
    "APP_JWT_SECRET",
    "test-secret-0123456789abcdef0123456789abcdef",
)

from app.core.config import get_settings  # noqa: E402
from app.db.session import reset_db  # noqa: E402
from app.main import app  # noqa: E402

_settings = get_settings()


@pytest.fixture(autouse=True)
async def _reset_state() -> AsyncGenerator[None, None]:
    """
    每个测试运行前：
      - drop + create 所有表（PostgreSQL）
      - FLUSHDB 清空 Redis 测试库

    不依赖 app lifespan，可单独运行。
    """
    await reset_db()

    if _settings.redis_url:
        redis = Redis.from_url(_settings.redis_url, decode_responses=True)
        try:
            await redis.flushdb()
        finally:
            await redis.aclose()

    yield


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    带 lifespan 的 httpx AsyncClient。

    进入时触发 app 的 startup（init_redis / init_arq），
    退出时触发 shutdown（close_redis / close_arq / close_db）。
    """
    async with LifespanManager(app) as manager:
        async with AsyncClient(
            transport=ASGITransport(app=manager.app),
            base_url="http://test",
        ) as ac:
            yield ac


@pytest.fixture
async def redis_client() -> AsyncGenerator[Redis, None]:
    """独立 Redis 客户端，供不经 HTTP 的缓存/任务单元测试使用。"""
    assert _settings.redis_url, "APP_REDIS_URL must be set for integration tests"
    r: Redis = Redis.from_url(_settings.redis_url, decode_responses=True)
    try:
        yield r
    finally:
        await r.aclose()
