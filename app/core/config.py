from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 默认 JWT 密钥，仅供本地开发使用；生产环境必须覆盖（见 _validate_production_safety）
DEFAULT_JWT_SECRET = "change-me-in-production-use-a-long-random-string"  # nosec B105


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
    host: str = "0.0.0.0"  # nosec B104 — intentional for containerized deployment, override via APP_HOST
    port: int = 8000
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    log_json: bool = False
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"])
    database_url: str = "sqlite+aiosqlite:///./app.db"
    sqlalchemy_echo: bool = False
    db_create_tables_on_startup: bool = True

    # JWT 认证
    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # Redis — 留空则禁用 Redis、缓存和任务队列
    redis_url: str | None = None

    # Sentry — 留空则禁用错误追踪
    sentry_dsn: str = ""

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def is_test(self) -> bool:
        return self.env == "test"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if value.strip() == "":
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    @model_validator(mode="after")
    def _validate_production_safety(self) -> Settings:
        """生产环境启动时对不安全配置 fail-fast，避免带着危险默认值上线。"""
        if not self.is_production:
            return self

        errors: list[str] = []
        if self.jwt_secret == DEFAULT_JWT_SECRET:
            errors.append("APP_JWT_SECRET 不能使用默认值，请设置一个高强度随机密钥")
        if self.allowed_origins == ["*"]:
            errors.append('APP_ALLOWED_ORIGINS 不能为通配符 ["*"]，请显式列出受信任来源')
        if self.db_create_tables_on_startup:
            errors.append(
                "APP_DB_CREATE_TABLES_ON_STARTUP 必须为 false，生产环境通过 Alembic 迁移建表"
            )
        if not self.database_url.startswith("postgresql"):
            errors.append("APP_DATABASE_URL 必须使用 PostgreSQL")
        if not self.log_json:
            errors.append("APP_LOG_JSON 必须为 true，生产环境需输出 JSON 结构化日志")

        if errors:
            raise ValueError("检测到不安全的生产配置：\n- " + "\n- ".join(errors))
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
