from __future__ import annotations

from fastapi import APIRouter

from app.auth.router import router as auth_router
from app.core.config import get_settings
from app.crawler.router import router as crawler_router
from app.health.router import router as health_router
from app.tenants.router import invitation_router
from app.tenants.router import router as tenants_router
from app.users.router import router as users_router

api_router = APIRouter(prefix=get_settings().api_v1_prefix)
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(tenants_router, prefix="/tenants", tags=["tenants"])
api_router.include_router(crawler_router, prefix="/tenants/{tenant_id}/crawler", tags=["crawler"])
api_router.include_router(
    invitation_router, prefix="/tenant-invitations", tags=["tenant-invitations"]
)
