from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core import arq as arq_module
from app.db import redis as redis_module


async def test_get_arq_raises_without_init(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(arq_module, "_pool", None)
    with pytest.raises(RuntimeError, match="Arq 未初始化"):
        await arq_module.get_arq()


async def test_get_redis_raises_without_init(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(redis_module, "_redis", None)
    with pytest.raises(RuntimeError, match="Redis 未初始化"):
        await redis_module.get_redis()


async def test_get_arq_returns_pool_when_initialized(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = AsyncMock()
    monkeypatch.setattr(arq_module, "_pool", pool)

    assert await arq_module.get_arq() is pool
