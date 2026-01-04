from pydantic import BaseModel

from app.infrastructure.constants import Pagination


class CursorParams(BaseModel):
    cursor: str | None = None
    limit: int = Pagination.DEFAULT_CURSOR_LIMIT


class OffsetParams(BaseModel):
    page: int = 1
    page_size: int = Pagination.DEFAULT_PAGE_SIZE

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size
