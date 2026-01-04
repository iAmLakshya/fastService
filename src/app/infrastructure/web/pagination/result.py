from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from app.infrastructure.web.pagination.schemas import PaginatedResponse

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class PageResult(Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size if self.total > 0 else 0

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    def to_response(
        self,
        item_mapper: Callable[[T], R] | None = None,
    ) -> "PaginatedResponse[R]":
        from app.infrastructure.web.pagination.schemas import PaginatedResponse

        items = [item_mapper(item) for item in self.items] if item_mapper else self.items
        return PaginatedResponse(
            items=items,
            total=self.total,
            page=self.page,
            page_size=self.page_size,
            total_pages=self.total_pages,
            has_next=self.has_next,
            has_prev=self.has_prev,
        )


@dataclass
class CursorResult(Generic[T]):
    items: list[T]
    next_cursor: str | None
    prev_cursor: str | None
    has_next: bool
    has_prev: bool
