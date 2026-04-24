from __future__ import annotations

from app.core.schemas import CustomModel


class LoginRequest(CustomModel):
    email: str
    password: str


class RefreshRequest(CustomModel):
    refresh_token: str


class TokenResponse(CustomModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
