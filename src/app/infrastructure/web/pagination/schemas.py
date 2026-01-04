from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class CursorPaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None
    prev_cursor: str | None
    has_next: bool
    has_prev: bool
