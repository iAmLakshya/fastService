from collections.abc import Sequence
from typing import Any, Protocol, TypeVar, runtime_checkable

from app.infrastructure.constants import Pagination

T = TypeVar("T")


@runtime_checkable
class ReadableRepository(Protocol[T]):
    async def find_by_id(self, entity_id: str, include_deleted: bool = False) -> T | None: ...
    async def find_all(
        self,
        offset: int = 0,
        limit: int = Pagination.DEFAULT_LIMIT,
        include_deleted: bool = False,
    ) -> list[T]: ...
    async def find_by_ids(
        self, entity_ids: list[str], include_deleted: bool = False
    ) -> list[T]: ...
    async def exists(self, entity_id: str) -> bool: ...
    async def count(self, include_deleted: bool = False) -> int: ...


@runtime_checkable
class WritableRepository(Protocol[T]):  # type: ignore[misc]
    async def create(self, data: dict[str, Any]) -> T: ...
    async def update(self, entity_id: str, data: dict[str, Any]) -> T | None: ...
    async def delete(self, entity_id: str, hard: bool = False) -> bool: ...


@runtime_checkable
class BulkRepository(Protocol[T]):
    async def create_many(self, items: Sequence[dict[str, Any]]) -> list[T]: ...
    async def update_many(self, entity_ids: list[str], data: dict[str, Any]) -> int: ...
    async def delete_many(self, entity_ids: list[str], hard: bool = False) -> int: ...


@runtime_checkable
class PaginatedRepository(Protocol[T]):
    async def find_paginated(
        self,
        page: int = 1,
        page_size: int = Pagination.DEFAULT_PAGE_SIZE,
        include_deleted: bool = False,
    ) -> tuple[list[T], int]: ...
    async def find_by_cursor(
        self,
        cursor: str | None = None,
        limit: int = Pagination.DEFAULT_CURSOR_LIMIT,
        include_deleted: bool = False,
    ) -> list[T]: ...


@runtime_checkable
class SoftDeletableRepository(Protocol[T]):  # type: ignore[misc]
    async def restore(self, entity_id: str) -> T | None: ...


@runtime_checkable
class UpsertableRepository(Protocol[T]):  # type: ignore[misc]
    async def upsert(
        self,
        data: dict[str, Any],
        conflict_fields: list[str],
        update_fields: list[str] | None = None,
    ) -> T: ...
    async def find_or_create(
        self, defaults: dict[str, Any] | None = None, **filters: Any
    ) -> tuple[T, bool]: ...


@runtime_checkable
class Repository(
    ReadableRepository[T],
    WritableRepository[T],
    BulkRepository[T],
    PaginatedRepository[T],
    SoftDeletableRepository[T],
    UpsertableRepository[T],
    Protocol[T],
):
    pass
