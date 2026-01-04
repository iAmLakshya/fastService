from typing import Any, Generic, NoReturn, TypeVar, cast, get_args, get_origin

from app.infrastructure.constants import Pagination
from app.infrastructure.persistence.model import Base
from app.infrastructure.persistence.repository.sql import BaseSQLRepository
from app.infrastructure.web.exceptions import NotFoundError
from app.infrastructure.web.pagination import (
    CursorResult,
    PageResult,
    decode_cursor,
    encode_cursor,
)

ModelT = TypeVar("ModelT", bound=Base)
RepoT = TypeVar("RepoT", bound=BaseSQLRepository[Any])


def _extract_generic_args(cls: type) -> tuple[type | None, type | None]:
    for base in getattr(cls, "__orig_bases__", []):
        origin = get_origin(base)
        if origin is not None:
            args = get_args(base)
            if len(args) >= 2:
                model_type = args[0] if isinstance(args[0], type) else None
                repo_type = args[1] if isinstance(args[1], type) else None
                return model_type, repo_type
    return None, None


class BaseService(Generic[ModelT, RepoT]):
    repository_class: type[RepoT]
    resource_name: str = "Resource"

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        model_type, repo_type = _extract_generic_args(cls)

        if repo_type is not None and not hasattr(cls, "repository_class"):
            cls.repository_class = repo_type

        if model_type is not None and cls.resource_name == "Resource":
            cls.resource_name = model_type.__name__

    def __init__(self, repository: RepoT | None = None) -> None:
        self._repo: RepoT = repository if repository is not None else self.repository_class()

    def _raise_not_found(self, entity_id: str) -> NoReturn:
        raise NotFoundError(self.resource_name, entity_id)

    async def find_by_id(self, entity_id: str) -> ModelT:
        entity = await self._repo.find_by_id(entity_id)
        if not entity:
            self._raise_not_found(entity_id)
        return cast(ModelT, entity)

    async def find_all(
        self,
        offset: int = 0,
        limit: int = Pagination.DEFAULT_LIMIT,
        include_deleted: bool = False,
    ) -> list[ModelT]:
        return await self._repo.find_all(offset, limit, include_deleted)

    async def find_paginated(
        self,
        page: int = 1,
        page_size: int = Pagination.DEFAULT_PAGE_SIZE,
        include_deleted: bool = False,
    ) -> PageResult[ModelT]:
        items, total = await self._repo.find_paginated(page, page_size, include_deleted)
        return PageResult(items=items, total=total, page=page, page_size=page_size)

    async def find_by_cursor(
        self,
        cursor: str | None = None,
        limit: int = Pagination.DEFAULT_CURSOR_LIMIT,
        include_deleted: bool = False,
    ) -> CursorResult[ModelT]:
        decoded = decode_cursor(cursor) if cursor else None
        items = await self._repo.find_by_cursor(decoded, limit, include_deleted)
        return self._build_cursor_result(items, limit, decoded)

    def _build_cursor_result(
        self,
        items: list[ModelT],
        limit: int,
        previous_cursor: str | None,
    ) -> CursorResult[ModelT]:
        has_more = len(items) > limit
        paginated_items = items[:limit] if has_more else items

        next_cursor = None
        if has_more and paginated_items:
            last_item = paginated_items[-1]
            next_cursor = encode_cursor(last_item.id)  # type: ignore[attr-defined]

        prev_cursor = encode_cursor(previous_cursor) if previous_cursor else None

        return CursorResult(
            items=paginated_items,
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            has_next=has_more,
            has_prev=prev_cursor is not None,
        )

    async def create(self, data: dict[str, object]) -> ModelT:
        return cast(ModelT, await self._repo.create(data))

    async def update(self, entity_id: str, data: dict[str, object]) -> ModelT:
        if not data:
            return await self.find_by_id(entity_id)
        entity = await self._repo.update(entity_id, data)
        if not entity:
            self._raise_not_found(entity_id)
        return cast(ModelT, entity)

    async def delete(self, entity_id: str, hard: bool = False) -> None:
        deleted = await self._repo.delete(entity_id, hard)
        if not deleted:
            self._raise_not_found(entity_id)

    async def restore(self, entity_id: str) -> ModelT:
        entity = await self._repo.restore(entity_id)
        if not entity:
            self._raise_not_found(entity_id)
        return cast(ModelT, entity)

    async def exists(self, entity_id: str) -> bool:
        return await self._repo.exists(entity_id)

    async def count(self, include_deleted: bool = False) -> int:
        return await self._repo.count(include_deleted)

    async def find_or_create(
        self,
        defaults: dict[str, object] | None = None,
        **filters: object,
    ) -> tuple[ModelT, bool]:
        return await self._repo.find_or_create(defaults, **filters)

    async def create_many(self, items: list[dict[str, object]]) -> list[ModelT]:
        return await self._repo.create_many(items)

    async def update_many(self, entity_ids: list[str], data: dict[str, object]) -> int:
        return await self._repo.update_many(entity_ids, data)

    async def delete_many(self, entity_ids: list[str], hard: bool = False) -> int:
        return await self._repo.delete_many(entity_ids, hard)
