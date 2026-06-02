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

from app.core.config import get_settings
from app.core.limiter import limiter
from app.db.session import reset_db
from app.main import app

_settings = get_settings()


@pytest.fixture(autouse=True)
async def _reset_state() -> AsyncGenerator[None, None]:
    """
    每个测试运行前：
      - drop + create 所有表（PostgreSQL）
      - FLUSHDB 清空 Redis 测试库

    不依赖 app lifespan，可单独运行。
    """
    limiter._storage.reset()
    await reset_db()

    if _settings.redis_url:
        redis = Redis.from_url(_settings.redis_url, decode_responses=True)
        try:
            await redis.flushdb()
        finally:
            await redis.aclose()

    yield


class _FreshRequestState:
    """为每个 HTTP 请求复制一份独立的 scope["state"]。

    asgi-lifespan 的 LifespanManager 会把同一个 state dict 注入到每个请求的 scope，
    导致 request.state 在请求间共享（真实服务器如 uvicorn 会按请求浅拷贝，不会共享）。
    这会让依赖 request.state 的中间件/装饰器（如 slowapi 的限流标记）只在首个请求生效。
    这里在最内层按请求浅拷贝 state，使测试环境与生产服务器行为一致。
    """

    def __init__(self, app: object) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: object, send: object) -> None:
        if scope["type"] == "http":
            scope = {**scope, "state": dict(scope.get("state") or {})}
        await self.app(scope, receive, send)  # type: ignore[operator]


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    带 lifespan 的 httpx AsyncClient。

    进入时触发 app 的 startup（init_redis / init_arq），
    退出时触发 shutdown（close_redis / close_arq / close_db）。
    """
    async with LifespanManager(_FreshRequestState(app)) as manager:
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
