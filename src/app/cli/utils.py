import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.core.context import _clear_sessions, _set_session
from app.infrastructure.persistence.adapters import (
    SQLAlchemyAdapter,
    SQLConfig,
    get_registry,
)


def run_async[T](coro: Awaitable[T]) -> T:
    return asyncio.get_event_loop().run_until_complete(coro)


async def _ensure_sql_adapter() -> SQLAlchemyAdapter:
    registry = get_registry()
    adapter_name = settings.databases.sql.name
    if not registry.has(adapter_name):
        sql_config = SQLConfig(
            url=settings.databases.sql.url,
            echo=settings.databases.sql.echo,
            pool_size=settings.databases.sql.pool_size,
            max_overflow=settings.databases.sql.max_overflow,
        )
        adapter = SQLAlchemyAdapter(sql_config)
        registry.register(adapter_name, adapter, set_as_default=True)
        await adapter.connect()
    return registry.get_typed(adapter_name, SQLAlchemyAdapter)


@asynccontextmanager
async def db_session() -> AsyncIterator[AsyncSession]:
    adapter = await _ensure_sql_adapter()
    async with adapter.session() as session:
        _set_session(settings.databases.sql.name, session)
        try:
            yield session
        finally:
            _clear_sessions()


def with_db_session[T](func: Callable[..., Awaitable[T]]) -> Callable[..., T]:
    def wrapper(*args: Any, **kwargs: Any) -> T:
        async def execute() -> T:
            async with db_session():
                return await func(*args, **kwargs)

        return run_async(execute())

    return wrapper
