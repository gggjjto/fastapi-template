from __future__ import annotations

import pytest

from app.db import redis as redis_module


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    return None


async def test_get_redis_raises_without_init(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(redis_module, "_redis", None)
    with pytest.raises(RuntimeError, match="Redis 未初始化"):
        await redis_module.get_redis()
