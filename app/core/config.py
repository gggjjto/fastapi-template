from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    project_name: str = "FastAPI Template"
    env: Literal["development", "staging", "production", "test"] = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    log_json: bool = False
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"])
    database_url: str = "sqlite+aiosqlite:///./app.db"
    sqlalchemy_echo: bool = False
    db_create_tables_on_startup: bool = True

    # JWT 认证
    jwt_secret: str = "change-me-in-production-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # Redis — 留空则禁用 Redis、缓存和任务队列
    redis_url: str | None = None

    # Sentry — 留空则禁用错误追踪
    sentry_dsn: str = ""

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if value.strip() == "":
            return []
        return [item.strip() for item in value.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
