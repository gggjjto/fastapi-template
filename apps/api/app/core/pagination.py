from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query
from pydantic import Field

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
    items: list[T] = Field(description="当前页数据列表")
    total: int = Field(description="数据总条数", ge=0)
    limit: int = Field(description="每页条数", ge=1, le=100)
    offset: int = Field(description="跳过条数", ge=0)
