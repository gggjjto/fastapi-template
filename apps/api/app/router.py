from __future__ import annotations

from fastapi import APIRouter

from app.auth.router import router as auth_router
from app.core.config import get_settings
from app.health.router import router as health_router
from app.users.router import router as users_router

api_router = APIRouter(prefix=get_settings().api_v1_prefix)
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
