from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import DEFAULT_JWT_SECRET, Settings

# 一份完全合规的生产配置，单测中按需覆盖其中一项制造违规。
_VALID_PROD: dict[str, object] = {
    "env": "production",
    "jwt_secret": "a-strong-random-production-secret-value-1234567890",
    "allowed_origins": ["https://app.example.com"],
    "db_create_tables_on_startup": False,
    "database_url": "postgresql+asyncpg://user:pass@db:5432/app",
    "log_json": True,
}


def _make(**overrides: object) -> Settings:
    # _env_file=None 关闭 .env 加载，避免本地文件干扰断言。
    return Settings(_env_file=None, **{**_VALID_PROD, **overrides})  # type: ignore[arg-type]


def test_valid_production_config_passes() -> None:
    settings = _make()
    assert settings.is_production
    assert not settings.is_test


def test_default_jwt_secret_rejected_in_production() -> None:
    with pytest.raises(ValidationError, match="APP_JWT_SECRET"):
        _make(jwt_secret=DEFAULT_JWT_SECRET)


def test_wildcard_cors_rejected_in_production() -> None:
    with pytest.raises(ValidationError, match="APP_ALLOWED_ORIGINS"):
        _make(allowed_origins=["*"])


def test_create_tables_rejected_in_production() -> None:
    with pytest.raises(ValidationError, match="APP_DB_CREATE_TABLES_ON_STARTUP"):
        _make(db_create_tables_on_startup=True)


def test_non_postgres_db_rejected_in_production() -> None:
    with pytest.raises(ValidationError, match="APP_DATABASE_URL"):
        _make(database_url="sqlite+aiosqlite:///./app.db")


def test_non_json_logs_rejected_in_production() -> None:
    with pytest.raises(ValidationError, match="APP_LOG_JSON"):
        _make(log_json=False)


def test_development_allows_insecure_defaults() -> None:
    # 非生产环境不触发安全校验，便于本地开箱即用。
    settings = Settings(
        _env_file=None,
        env="development",
        jwt_secret=DEFAULT_JWT_SECRET,
        allowed_origins=["*"],
    )
    assert not settings.is_production
