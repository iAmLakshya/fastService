from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.infrastructure.persistence.adapters.protocols import DatabaseType


@dataclass(frozen=True)
class SQLConfig:
    url: str
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    pool_pre_ping: bool = True
    pool_recycle: int = 3600


class SQLAlchemyAdapter:
    def __init__(self, config: SQLConfig) -> None:
        self._config = config
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def database_type(self) -> DatabaseType:
        return DatabaseType.SQL

    @property
    def is_connected(self) -> bool:
        return self._engine is not None

    @property
    def config(self) -> SQLConfig:
        return self._config

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError("Adapter not connected")
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            raise RuntimeError("Adapter not connected")
        return self._session_factory

    def _is_sqlite(self) -> bool:
        return self._config.url.startswith("sqlite")

    async def connect(self) -> None:
        if self._engine is not None:
            return

        engine_kwargs: dict[str, object] = {"echo": self._config.echo}

        if not self._is_sqlite():
            engine_kwargs.update(
                {
                    "pool_size": self._config.pool_size,
                    "max_overflow": self._config.max_overflow,
                    "pool_pre_ping": self._config.pool_pre_ping,
                    "pool_recycle": self._config.pool_recycle,
                }
            )

        self._engine = create_async_engine(self._config.url, **engine_kwargs)
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    async def disconnect(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    async def dispose(self) -> None:
        await self.disconnect()

    async def health_check(self) -> bool:
        if not self.is_connected or self._session_factory is None:
            return False
        try:
            async with self._session_factory() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession]:
        if self._session_factory is None:
            raise RuntimeError("Adapter not connected")
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    def configure_for_testing(
        self,
        engine: AsyncEngine,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._engine = engine
        self._session_factory = session_factory


class ReadOnlySQLAlchemyAdapter(SQLAlchemyAdapter):
    async def connect(self) -> None:
        if self._engine is not None:
            return

        engine_kwargs: dict[str, object] = {"echo": self._config.echo}

        if not self._is_sqlite():
            engine_kwargs.update(
                {
                    "pool_size": self._config.pool_size,
                    "max_overflow": self._config.max_overflow,
                    "pool_pre_ping": self._config.pool_pre_ping,
                    "pool_recycle": self._config.pool_recycle,
                }
            )

        self._engine = create_async_engine(
            self._config.url,
            execution_options={"postgresql_readonly": True, "sqlite_readonly": True},
            **engine_kwargs,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession]:
        if self._session_factory is None:
            raise RuntimeError("Adapter not connected")
        session = self._session_factory()
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()
