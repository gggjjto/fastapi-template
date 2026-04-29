from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.core.response import ApiResponse
from app.db.session import DBSession

router = APIRouter()
settings = get_settings()


@router.get(
    "/live",
    response_model=ApiResponse[dict[str, str]],
    summary="存活探针",
    description=(
        "Liveness Probe：返回服务名称，证明进程正在运行。\n\n"
        "Kubernetes 通过此接口判断容器是否需要重启。"
    ),
)
async def live() -> ApiResponse[dict[str, str]]:
    return ApiResponse.ok({"status": "alive", "service": settings.project_name})


@router.get(
    "/ready",
    response_model=ApiResponse[dict[str, str]],
    summary="就绪探针",
    description=(
        "Readiness Probe：执行 `SELECT 1` 验证数据库连接；若启用 Redis 则同时执行 PING。\n\n"
        "Kubernetes 通过此接口判断容器是否可以接收流量。"
        "数据库或 Redis 不可达时返回 500。"
    ),
)
async def ready(session: DBSession) -> ApiResponse[dict[str, str]]:
    await session.execute(text("SELECT 1"))
    result: dict[str, str] = {"status": "ready", "database": "ok"}
    if settings.redis_url:
        from app.db.redis import get_redis

        redis = await get_redis()
        await redis.ping()
        result["redis"] = "ok"
    return ApiResponse.ok(result)
