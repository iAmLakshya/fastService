from typing import Any, Generic, TypeVar, get_args, get_origin

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.core.context import get_db
from app.infrastructure.persistence.adapters import SQLAlchemyAdapter, get_registry
from app.infrastructure.persistence.model import Base
from app.infrastructure.persistence.repository.dialect import get_upsert_strategy
from app.infrastructure.persistence.repository.sql.mixins import (
    SQLBulkMixin,
    SQLPaginationMixin,
    SQLSoftDeleteMixin,
    SQLUpsertMixin,
    SQLWriteMixin,
)

ModelT = TypeVar("ModelT", bound=Base)


def _extract_model_type(cls: type) -> type | None:
    for base in getattr(cls, "__orig_bases__", []):
        origin = get_origin(base)
        if origin is not None:
            args = get_args(base)
            if args and isinstance(args[0], type):
                return args[0]
    return None


class BaseSQLRepository(
    SQLWriteMixin[ModelT],
    SQLBulkMixin[ModelT],
    SQLPaginationMixin[ModelT],
    SQLSoftDeleteMixin[ModelT],
    SQLUpsertMixin[ModelT],
    Generic[ModelT],
):
    model: type[ModelT]
    adapter_name: str = "primary"

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "model") or cls.model is None:
            model_type = _extract_model_type(cls)
            if model_type is not None:
                cls.model = model_type

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._explicit_session = session
        self._adapter: SQLAlchemyAdapter | None = None
        adapter = self._get_adapter()
        self._upsert_strategy = get_upsert_strategy(adapter.config.url)

    def _get_adapter(self) -> SQLAlchemyAdapter:
        if self._adapter is None:
            registry = get_registry()
            self._adapter = registry.get_typed(self.adapter_name, SQLAlchemyAdapter)
        return self._adapter

    @property
    def _session(self) -> AsyncSession:  # type: ignore[override]
        if self._explicit_session is not None:
            return self._explicit_session
        return get_db(self.adapter_name)
