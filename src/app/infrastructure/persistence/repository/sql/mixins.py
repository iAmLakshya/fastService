from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Generic, Protocol, TypeVar, cast

from sqlalchemy import CursorResult, delete, func, select, update

from app.infrastructure.constants import Pagination

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.sql import Select

    from app.infrastructure.persistence.model import Base

ModelT = TypeVar("ModelT", bound="Base")


class UpsertStrategy(Protocol):
    supports_returning: bool

    def build_upsert(
        self,
        model: type[Any],
        data: dict[str, object],
        conflict_fields: list[str],
        update_fields: list[str],
    ) -> Any: ...


def _supports_soft_delete(model: type[Any]) -> bool:
    return hasattr(model, "is_deleted")


def _exclude_deleted[SelectT: "Select[Any]"](stmt: SelectT, model: type[Any]) -> SelectT:
    if _supports_soft_delete(model):
        stmt = stmt.where(model.is_deleted.is_(False))
    return stmt


class SQLReadMixin(Generic[ModelT]):
    model: type[ModelT]
    _session: "AsyncSession"

    async def find_by_id(self, entity_id: str, include_deleted: bool = False) -> ModelT | None:
        stmt = select(self.model).where(self.model.id == entity_id)  # type: ignore[attr-defined]
        if not include_deleted:
            stmt = _exclude_deleted(stmt, self.model)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_all(
        self,
        offset: int = 0,
        limit: int = Pagination.DEFAULT_LIMIT,
        include_deleted: bool = False,
    ) -> list[ModelT]:
        stmt = select(self.model)
        if not include_deleted:
            stmt = _exclude_deleted(stmt, self.model)
        stmt = stmt.order_by(self.model.id).offset(offset).limit(limit)  # type: ignore[attr-defined]
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_ids(
        self,
        entity_ids: list[str],
        include_deleted: bool = False,
    ) -> list[ModelT]:
        if not entity_ids:
            return []
        stmt = select(self.model).where(self.model.id.in_(entity_ids))  # type: ignore[attr-defined]
        if not include_deleted:
            stmt = _exclude_deleted(stmt, self.model)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_where(
        self,
        include_deleted: bool = False,
        **conditions: object,
    ) -> list[ModelT]:
        stmt = select(self.model).filter_by(**conditions)
        if not include_deleted:
            stmt = _exclude_deleted(stmt, self.model)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def exists(self, entity_id: str) -> bool:
        stmt = select(func.count()).select_from(self.model).where(self.model.id == entity_id)  # type: ignore[attr-defined]
        stmt = _exclude_deleted(stmt, self.model)
        result = await self._session.execute(stmt)
        return result.scalar_one() > 0

    async def count(self, include_deleted: bool = False) -> int:
        stmt = select(func.count()).select_from(self.model)
        if not include_deleted:
            stmt = _exclude_deleted(stmt, self.model)
        result = await self._session.execute(stmt)
        return result.scalar_one()


class SQLWriteMixin(Generic[ModelT]):
    model: type[ModelT]
    _session: "AsyncSession"

    async def create(self, data: dict[str, object]) -> ModelT:
        entity = self.model(**data)
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def update(self, entity_id: str, data: dict[str, object]) -> ModelT | None:
        stmt = (
            update(self.model)
            .where(self.model.id == entity_id)  # type: ignore[attr-defined]
            .values(**data)
            .returning(self.model)
        )
        if _supports_soft_delete(self.model):
            stmt = stmt.where(self.model.is_deleted.is_(False))  # type: ignore[attr-defined]
        result = await self._session.execute(stmt)
        entity = result.scalar_one_or_none()
        if entity:
            await self._session.refresh(entity)
        return entity

    async def delete(self, entity_id: str, hard: bool = False) -> bool:
        if hard or not _supports_soft_delete(self.model):
            return await self._hard_delete(entity_id)
        return await self._soft_delete(entity_id)

    async def _hard_delete(self, entity_id: str) -> bool:
        stmt = delete(self.model).where(self.model.id == entity_id)  # type: ignore[attr-defined]
        result = cast(CursorResult[Any], await self._session.execute(stmt))
        return result.rowcount > 0

    async def _soft_delete(self, entity_id: str) -> bool:
        stmt = (
            update(self.model)
            .where(self.model.id == entity_id)  # type: ignore[attr-defined]
            .where(self.model.is_deleted.is_(False))  # type: ignore[attr-defined]
            .values(is_deleted=True, deleted_at=datetime.now(UTC))
        )
        result = cast(CursorResult[Any], await self._session.execute(stmt))
        return result.rowcount > 0


class SQLBulkMixin(Generic[ModelT]):
    model: type[ModelT]
    _session: "AsyncSession"

    async def create_many(self, items: Sequence[dict[str, object]]) -> list[ModelT]:
        if not items:
            return []
        entities = [self.model(**item) for item in items]
        self._session.add_all(entities)
        await self._session.flush()
        for entity in entities:
            await self._session.refresh(entity)
        return entities

    async def update_many(self, entity_ids: list[str], data: dict[str, object]) -> int:
        if not entity_ids:
            return 0
        stmt = update(self.model).where(self.model.id.in_(entity_ids)).values(**data)  # type: ignore[attr-defined]
        if _supports_soft_delete(self.model):
            stmt = stmt.where(self.model.is_deleted.is_(False))  # type: ignore[attr-defined]
        result = cast(CursorResult[Any], await self._session.execute(stmt))
        return result.rowcount

    async def delete_many(self, entity_ids: list[str], hard: bool = False) -> int:
        if not entity_ids:
            return 0
        if hard or not _supports_soft_delete(self.model):
            return await self._hard_delete_many(entity_ids)
        return await self._soft_delete_many(entity_ids)

    async def _hard_delete_many(self, entity_ids: list[str]) -> int:
        stmt = delete(self.model).where(self.model.id.in_(entity_ids))  # type: ignore[attr-defined]
        result = cast(CursorResult[Any], await self._session.execute(stmt))
        return result.rowcount

    async def _soft_delete_many(self, entity_ids: list[str]) -> int:
        stmt = (
            update(self.model)
            .where(self.model.id.in_(entity_ids))  # type: ignore[attr-defined]
            .where(self.model.is_deleted.is_(False))  # type: ignore[attr-defined]
            .values(is_deleted=True, deleted_at=datetime.now(UTC))
        )
        result = cast(CursorResult[Any], await self._session.execute(stmt))
        return result.rowcount


class SQLPaginationMixin(SQLReadMixin[ModelT], Generic[ModelT]):
    async def find_paginated(
        self,
        page: int = 1,
        page_size: int = Pagination.DEFAULT_PAGE_SIZE,
        include_deleted: bool = False,
    ) -> tuple[list[ModelT], int]:
        total = await self.count(include_deleted=include_deleted)
        offset = (page - 1) * page_size
        stmt = select(self.model)
        if not include_deleted:
            stmt = _exclude_deleted(stmt, self.model)
        stmt = stmt.order_by(self.model.id).offset(offset).limit(page_size)  # type: ignore[attr-defined]
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def find_by_cursor(
        self,
        cursor: str | None = None,
        limit: int = Pagination.DEFAULT_CURSOR_LIMIT,
        include_deleted: bool = False,
    ) -> list[ModelT]:
        stmt = select(self.model)
        if not include_deleted:
            stmt = _exclude_deleted(stmt, self.model)
        if cursor:
            stmt = stmt.where(self.model.id > cursor)  # type: ignore[attr-defined]
        stmt = stmt.order_by(self.model.id).limit(limit + 1)  # type: ignore[attr-defined]
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class SQLSoftDeleteMixin(Generic[ModelT]):
    model: type[ModelT]
    _session: "AsyncSession"

    async def restore(self, entity_id: str) -> ModelT | None:
        if not _supports_soft_delete(self.model):
            return None
        stmt = (
            update(self.model)
            .where(self.model.id == entity_id)  # type: ignore[attr-defined]
            .where(self.model.is_deleted.is_(True))  # type: ignore[attr-defined]
            .values(is_deleted=False, deleted_at=None)
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        entity = result.scalar_one_or_none()
        if entity:
            await self._session.refresh(entity)
        return entity


class SQLUpsertMixin(Generic[ModelT]):
    model: type[ModelT]
    _session: "AsyncSession"
    _upsert_strategy: UpsertStrategy

    async def upsert(
        self,
        data: dict[str, object],
        conflict_fields: list[str],
        update_fields: list[str] | None = None,
    ) -> ModelT:
        fields_to_update = update_fields or [k for k in data if k not in conflict_fields]
        stmt = self._upsert_strategy.build_upsert(
            self.model, data, conflict_fields, fields_to_update
        )
        await self._session.execute(stmt)

        if self._upsert_strategy.supports_returning:
            await self._session.flush()

        filters = {field: data[field] for field in conflict_fields}
        query = select(self.model).filter_by(**filters)
        result = await self._session.execute(query)
        return result.scalar_one()

    async def find_or_create(
        self,
        defaults: dict[str, object] | None = None,
        **filters: object,
    ) -> tuple[ModelT, bool]:
        stmt = select(self.model).filter_by(**filters)
        stmt = _exclude_deleted(stmt, self.model)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing, False

        create_data = {**filters, **(defaults or {})}
        entity = self.model(**create_data)
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity, True
