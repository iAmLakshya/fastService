from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure import AppException, Base
from app.infrastructure.messaging.events import clear_handlers
from app.infrastructure.persistence.adapters import (
    SQLAlchemyAdapter,
    SQLConfig,
    get_registry,
    reset_registry,
)
from app.infrastructure.web.exceptions import app_exception_handler
from app.modules.todos.model import Todo  # noqa: F401
from tests.factories import BaseFactory, TodoFactory


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def cleanup_event_handlers() -> Iterator[None]:
    yield
    clear_handlers()


@pytest.fixture
async def db_engine() -> AsyncIterator[Any]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_adapter(db_engine: Any) -> AsyncIterator[SQLAlchemyAdapter]:
    reset_registry()

    config = SQLConfig(url="sqlite+aiosqlite:///:memory:")
    adapter = SQLAlchemyAdapter(config)

    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    adapter.configure_for_testing(db_engine, session_factory)

    registry = get_registry()
    registry.register("primary", adapter, set_as_default=True)

    yield adapter

    reset_registry()


@pytest.fixture
async def db_session(db_adapter: SQLAlchemyAdapter) -> AsyncIterator[AsyncSession]:
    from app.infrastructure.core.context import _clear_sessions, _set_session

    async with (
        db_adapter.engine.connect() as conn,
        AsyncSession(bind=conn) as session,
    ):
        _set_session("primary", session)
        yield session
        _clear_sessions()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:  # noqa: ARG001
    from fastapi import FastAPI

    from app.router import router

    app = FastAPI()
    app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]
    app.include_router(router)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy"}

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


class BoundTodoFactory:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def build(self, **kwargs: Any) -> Todo:
        return TodoFactory.build(**kwargs)

    async def create(self, **kwargs: Any) -> Todo:
        return await TodoFactory.create(self._session, **kwargs)

    async def create_batch(self, count: int, **kwargs: Any) -> list[Todo]:
        return await TodoFactory.create_batch(self._session, count, **kwargs)


@pytest.fixture
def todo_factory(db_session: AsyncSession) -> BoundTodoFactory:
    return BoundTodoFactory(db_session)


class BoundFactory:
    def __init__(
        self, factory_class: type[BaseFactory[Any]], session: AsyncSession
    ) -> None:
        self._factory_class = factory_class
        self._session = session

    def build(self, **kwargs: Any) -> Any:
        return self._factory_class.build(**kwargs)

    async def create(self, **kwargs: Any) -> Any:
        return await self._factory_class.create(self._session, **kwargs)

    async def create_batch(self, count: int, **kwargs: Any) -> list[Any]:
        return await self._factory_class.create_batch(self._session, count, **kwargs)


class FactoryManager:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def get(self, factory_class: type[BaseFactory[Any]]) -> BoundFactory:
        return BoundFactory(factory_class, self._session)


@pytest.fixture
def factory(db_session: AsyncSession) -> FactoryManager:
    return FactoryManager(db_session)
