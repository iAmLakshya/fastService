from collections.abc import Iterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.adapters import (
    DatabaseRegistry,
    SQLAlchemyAdapter,
    SQLConfig,
    get_registry,
    reset_registry,
)
from app.infrastructure.persistence.adapters.protocols import DatabaseType
from app.infrastructure.persistence.adapters.sqlalchemy import ReadOnlySQLAlchemyAdapter


class TestSQLConfig:
    def test_default_values(self) -> None:
        config = SQLConfig(url="sqlite+aiosqlite:///:memory:")
        assert config.echo is False
        assert config.pool_size == 5
        assert config.max_overflow == 10
        assert config.pool_pre_ping is True
        assert config.pool_recycle == 3600

    def test_custom_values(self) -> None:
        config = SQLConfig(
            url="postgresql+asyncpg://user:pass@localhost/db",
            echo=True,
            pool_size=20,
            max_overflow=5,
            pool_pre_ping=False,
            pool_recycle=1800,
        )
        assert config.url == "postgresql+asyncpg://user:pass@localhost/db"
        assert config.echo is True
        assert config.pool_size == 20

    def test_immutable(self) -> None:
        config = SQLConfig(url="sqlite+aiosqlite:///:memory:")
        with pytest.raises(AttributeError):
            config.url = "new_url"  # type: ignore[misc]


class TestSQLAlchemyAdapter:
    @pytest.fixture
    def config(self) -> SQLConfig:
        return SQLConfig(url="sqlite+aiosqlite:///:memory:", echo=False)

    @pytest.fixture
    def adapter(self, config: SQLConfig) -> SQLAlchemyAdapter:
        return SQLAlchemyAdapter(config)

    def test_initial_state(self, adapter: SQLAlchemyAdapter) -> None:
        assert adapter.database_type == DatabaseType.SQL
        assert adapter.is_connected is False
        assert adapter.config.url == "sqlite+aiosqlite:///:memory:"

    @pytest.mark.anyio
    async def test_connect_creates_engine(self, adapter: SQLAlchemyAdapter) -> None:
        await adapter.connect()
        try:
            assert adapter.is_connected is True
            assert adapter.engine is not None
            assert adapter._session_factory is not None
        finally:
            await adapter.disconnect()

    @pytest.mark.anyio
    async def test_connect_idempotent(self, adapter: SQLAlchemyAdapter) -> None:
        await adapter.connect()
        engine1 = adapter.engine
        await adapter.connect()
        engine2 = adapter.engine
        assert engine1 is engine2
        await adapter.disconnect()

    @pytest.mark.anyio
    async def test_disconnect(self, adapter: SQLAlchemyAdapter) -> None:
        await adapter.connect()
        assert adapter.is_connected is True
        await adapter.disconnect()
        assert adapter.is_connected is False

    @pytest.mark.anyio
    async def test_health_check_connected(self, adapter: SQLAlchemyAdapter) -> None:
        await adapter.connect()
        try:
            result = await adapter.health_check()
            assert result is True
        finally:
            await adapter.disconnect()

    @pytest.mark.anyio
    async def test_health_check_not_connected(self, adapter: SQLAlchemyAdapter) -> None:
        result = await adapter.health_check()
        assert result is False

    @pytest.mark.anyio
    async def test_session_context_manager(self, adapter: SQLAlchemyAdapter) -> None:
        await adapter.connect()
        try:
            async with adapter.session() as session:
                assert isinstance(session, AsyncSession)
        finally:
            await adapter.disconnect()

    @pytest.mark.anyio
    async def test_session_commits_on_success(self, adapter: SQLAlchemyAdapter) -> None:
        await adapter.connect()
        try:
            async with adapter.session() as session:
                from sqlalchemy import text

                await session.execute(text("SELECT 1"))
        finally:
            await adapter.disconnect()

    @pytest.mark.anyio
    async def test_engine_raises_when_not_connected(
        self, adapter: SQLAlchemyAdapter
    ) -> None:
        with pytest.raises(RuntimeError, match="Adapter not connected"):
            _ = adapter.engine


class TestReadOnlySQLAlchemyAdapter:
    @pytest.fixture
    def config(self) -> SQLConfig:
        return SQLConfig(url="sqlite+aiosqlite:///:memory:")

    @pytest.fixture
    def adapter(self, config: SQLConfig) -> ReadOnlySQLAlchemyAdapter:
        return ReadOnlySQLAlchemyAdapter(config)

    @pytest.mark.anyio
    async def test_session_no_commit(self, adapter: ReadOnlySQLAlchemyAdapter) -> None:
        await adapter.connect()
        try:
            async with adapter.session() as session:
                assert isinstance(session, AsyncSession)
        finally:
            await adapter.disconnect()


class TestDatabaseRegistry:
    @pytest.fixture(autouse=True)
    def reset(self) -> Iterator[None]:
        reset_registry()
        yield
        reset_registry()

    @pytest.fixture
    def registry(self) -> DatabaseRegistry:
        return get_registry()

    @pytest.fixture
    def adapter(self) -> SQLAlchemyAdapter:
        return SQLAlchemyAdapter(SQLConfig(url="sqlite+aiosqlite:///:memory:"))

    def test_register_adapter(
        self, registry: DatabaseRegistry, adapter: SQLAlchemyAdapter
    ) -> None:
        registry.register("test", adapter)
        assert registry.has("test")
        assert registry.get("test") is adapter

    def test_register_sets_default(
        self, registry: DatabaseRegistry, adapter: SQLAlchemyAdapter
    ) -> None:
        registry.register("primary", adapter, set_as_default=True)
        default = registry.get_default(DatabaseType.SQL)
        assert default is adapter

    def test_first_adapter_becomes_default(
        self, registry: DatabaseRegistry, adapter: SQLAlchemyAdapter
    ) -> None:
        registry.register("first", adapter)
        default = registry.get_default(DatabaseType.SQL)
        assert default is adapter

    def test_register_duplicate_raises(
        self, registry: DatabaseRegistry, adapter: SQLAlchemyAdapter
    ) -> None:
        registry.register("test", adapter)
        with pytest.raises(ValueError, match="already registered"):
            registry.register("test", adapter)

    def test_register_replace(
        self, registry: DatabaseRegistry, adapter: SQLAlchemyAdapter
    ) -> None:
        registry.register("test", adapter)
        new_adapter = SQLAlchemyAdapter(SQLConfig(url="sqlite+aiosqlite:///new.db"))
        registry.register("test", new_adapter, replace=True)
        assert registry.get("test") is new_adapter

    def test_unregister(
        self, registry: DatabaseRegistry, adapter: SQLAlchemyAdapter
    ) -> None:
        registry.register("test", adapter)
        removed = registry.unregister("test")
        assert removed is adapter
        assert not registry.has("test")

    def test_get_typed(
        self, registry: DatabaseRegistry, adapter: SQLAlchemyAdapter
    ) -> None:
        registry.register("test", adapter)
        typed = registry.get_typed("test", SQLAlchemyAdapter)
        assert isinstance(typed, SQLAlchemyAdapter)

    def test_get_typed_wrong_type_raises(
        self, registry: DatabaseRegistry, adapter: SQLAlchemyAdapter
    ) -> None:
        from app.infrastructure.persistence.adapters import RedisAdapter

        registry.register("test", adapter)
        with pytest.raises(TypeError, match="is not of type"):
            registry.get_typed("test", RedisAdapter)

    def test_get_not_found_raises(self, registry: DatabaseRegistry) -> None:
        with pytest.raises(KeyError, match="not found"):
            registry.get("nonexistent")

    def test_has_type(
        self, registry: DatabaseRegistry, adapter: SQLAlchemyAdapter
    ) -> None:
        assert not registry.has_type(DatabaseType.SQL)
        registry.register("test", adapter)
        assert registry.has_type(DatabaseType.SQL)

    def test_names(
        self, registry: DatabaseRegistry, adapter: SQLAlchemyAdapter
    ) -> None:
        registry.register("one", adapter)
        registry.register("two", adapter, replace=True)
        assert set(registry.names) == {"one", "two"}

    @pytest.mark.anyio
    async def test_connect_all(
        self, registry: DatabaseRegistry, adapter: SQLAlchemyAdapter
    ) -> None:
        registry.register("test", adapter)
        await registry.connect_all()
        assert adapter.is_connected
        await registry.disconnect_all()

    @pytest.mark.anyio
    async def test_health_check_all(
        self, registry: DatabaseRegistry, adapter: SQLAlchemyAdapter
    ) -> None:
        registry.register("test", adapter)
        await registry.connect_all()
        try:
            results = await registry.health_check_all()
            assert results == {"test": True}
        finally:
            await registry.disconnect_all()

    def test_clear(
        self, registry: DatabaseRegistry, adapter: SQLAlchemyAdapter
    ) -> None:
        registry.register("test", adapter)
        registry.clear()
        assert len(registry) == 0

    def test_len(
        self, registry: DatabaseRegistry, adapter: SQLAlchemyAdapter
    ) -> None:
        assert len(registry) == 0
        registry.register("test", adapter)
        assert len(registry) == 1

    def test_contains(
        self, registry: DatabaseRegistry, adapter: SQLAlchemyAdapter
    ) -> None:
        assert "test" not in registry
        registry.register("test", adapter)
        assert "test" in registry

    def test_iter(
        self, registry: DatabaseRegistry, adapter: SQLAlchemyAdapter
    ) -> None:
        registry.register("test", adapter)
        items = list(registry)
        assert items == [("test", adapter)]
