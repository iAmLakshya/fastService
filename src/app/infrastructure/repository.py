from typing import Any, Generic, TypeVar

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.context import get_db
from app.infrastructure.model import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    @property
    def _session(self) -> AsyncSession:
        return get_db()

    async def get_by_id(self, id: str) -> ModelT | None:
        stmt = select(self.model).where(self.model.id == id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelT]:
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, data: dict[str, Any]) -> ModelT:
        instance = self.model(**data)
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def update(self, id: str, data: dict[str, Any]) -> ModelT | None:
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**data)
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        instance = result.scalar_one_or_none()
        if instance:
            await self._session.refresh(instance)
        return instance

    async def delete(self, id: str) -> bool:
        stmt = delete(self.model).where(self.model.id == id)
        result = await self._session.execute(stmt)
        return result.rowcount > 0
