from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure import Base
from app.modules.todos.model import Todo

ModelT = TypeVar("ModelT", bound=Base)


class BaseFactory(Generic[ModelT]):
    model: type[ModelT]
    defaults: dict[str, Any] = {}

    @classmethod
    def _generate_id(cls) -> str:
        return str(uuid4())

    @classmethod
    def _get_defaults(cls) -> dict[str, Any]:
        defaults: dict[str, Any] = {"id": cls._generate_id()}

        if hasattr(cls.model, "created_at"):
            defaults["created_at"] = datetime.now(UTC)
        if hasattr(cls.model, "updated_at"):
            defaults["updated_at"] = datetime.now(UTC)
        if hasattr(cls.model, "is_deleted"):
            defaults["is_deleted"] = False
        if hasattr(cls.model, "deleted_at"):
            defaults["deleted_at"] = None

        return {**defaults, **cls.defaults}

    @classmethod
    def build(cls, **overrides: Any) -> ModelT:
        data = {**cls._get_defaults(), **overrides}
        return cls.model(**data)

    @classmethod
    def build_batch(cls, count: int, **overrides: Any) -> list[ModelT]:
        return [cls.build(**overrides) for _ in range(count)]

    @classmethod
    async def create(cls, session: AsyncSession, **overrides: Any) -> ModelT:
        instance = cls.build(**overrides)
        session.add(instance)
        await session.flush()
        await session.refresh(instance)
        return instance

    @classmethod
    async def create_batch(
        cls, session: AsyncSession, count: int, **overrides: Any
    ) -> list[ModelT]:
        instances = []
        for _ in range(count):
            instance = await cls.create(session, **overrides)
            instances.append(instance)
        return instances


class TodoFactory(BaseFactory[Todo]):
    model = Todo
    defaults: dict[str, Any] = {
        "title": "Test Todo",
        "description": "Test description",
        "completed": False,
    }

    @classmethod
    def completed(cls, **overrides: Any) -> Todo:
        return cls.build(completed=True, **overrides)

    @classmethod
    def with_title(cls, title: str, **overrides: Any) -> Todo:
        return cls.build(title=title, **overrides)
