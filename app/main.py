from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.error_handlers import register_error_handlers
from app.core.limiter import limiter, rate_limit_handler
from app.core.logging import configure_logging
from app.core.middleware import RequestIDMiddleware
from app.core.sentry import init_sentry
from app.db.session import close_db, init_db
from app.router import api_router

settings = get_settings()
configure_logging(log_level=settings.log_level, json_logs=settings.log_json)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("app.startup", env=settings.env)

    if settings.db_create_tables_on_startup:
        await init_db()

    if settings.redis_url:
        from app.core.arq import init_arq
        from app.db.redis import init_redis

        await init_redis()
        await init_arq()
        logger.info("app.redis.connected", url=settings.redis_url)

    yield

    if settings.redis_url:
        from app.core.arq import close_arq
        from app.db.redis import close_redis

        await close_arq()
        await close_redis()

    await close_db()
    logger.info("app.shutdown")


def create_app() -> FastAPI:
    init_sentry(settings.sentry_dsn, settings.env)

    app_configs: dict[str, Any] = {
        "title": settings.project_name,
        "version": "0.1.0",
        "lifespan": lifespan,
    }

    # 非开发/测试环境隐藏 OpenAPI 文档，避免接口信息泄露
    if settings.env not in ("development", "test"):
        app_configs["openapi_url"] = None

    app = FastAPI(**app_configs)

    # 注册全局错误处理器
    register_error_handlers(app)
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

    # 将限流器挂载到 app state，slowapi 从此处读取
    app.state.limiter = limiter

    # 中间件按添加顺序逆序执行：最后添加的最先处理请求
    # RequestIDMiddleware 最外层，确保所有日志都能携带 request_id
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {"message": f"{settings.project_name} is running", "docs": "/docs"}

    app.include_router(api_router)
    return app


app = create_app()
