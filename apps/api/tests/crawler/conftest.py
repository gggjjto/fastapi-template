from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest

from app.db.base import Base
from app.db.session import engine


@pytest.fixture(autouse=True)
async def _create_crawler_tables(_reset_state: None) -> AsyncGenerator[None, None]:
    import app.crawler.domain.models  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield
