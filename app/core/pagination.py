from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query

from app.core.schemas import CustomModel


class PaginationParams:
    def __init__(
        self,
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> None:
        self.limit = limit
        self.offset = offset


Pagination = Annotated[PaginationParams, Depends(PaginationParams)]


class Page[T](CustomModel):
    items: list[T]
    total: int
    limit: int
    offset: int
