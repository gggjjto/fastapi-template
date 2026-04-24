from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.core.response import ApiResponse
from app.db.session import DBSession

router = APIRouter()
settings = get_settings()


@router.get("/live", response_model=ApiResponse[dict[str, str]])
async def live() -> ApiResponse[dict[str, str]]:
    """
    存活探针（Liveness Probe）。

    返回服务名称，证明进程正在运行。
    Kubernetes 通过此接口判断容器是否需要重启。
    """
    return ApiResponse.ok({"status": "alive", "service": settings.project_name})


@router.get("/ready", response_model=ApiResponse[dict[str, str]])
async def ready(session: DBSession) -> ApiResponse[dict[str, str]]:
    """
    就绪探针（Readiness Probe）。

    执行 `SELECT 1` 验证数据库连接是否正常。
    Kubernetes 通过此接口判断容器是否可以接收流量。
    数据库不可达时返回 500。
    """
    await session.execute(text("SELECT 1"))
    return ApiResponse.ok({"status": "ready", "database": "ok"})
