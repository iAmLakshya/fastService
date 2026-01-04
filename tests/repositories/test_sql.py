from collections.abc import AsyncIterator
from typing import Any

import pytest
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure import Base
from app.infrastructure.persistence.adapters import (
    SQLAlchemyAdapter,
    SQLConfig,
    get_registry,
    reset_registry,
)
from app.infrastructure.persistence.model import SoftDeletableModel
from app.infrastructure.persistence.repository import BaseSQLRepository


class Item(SoftDeletableModel):
    __tablename__ = "test_items"
    name: Mapped[str] = mapped_column(String(100), unique=True)
    category: Mapped[str] = mapped_column(String(50), default="default")
    value: Mapped[int] = mapped_column(default=0)


class ItemRepository(BaseSQLRepository[Item]):
    pass


@pytest.fixture(scope="function")
async def db_engine() -> AsyncIterator[Any]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def sql_adapter(db_engine: Any) -> AsyncIterator[SQLAlchemyAdapter]:
    reset_registry()
    config = SQLConfig(url="sqlite+aiosqlite:///:memory:")
    adapter = SQLAlchemyAdapter(config)
    adapter._engine = db_engine
    adapter._session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    registry = get_registry()
    registry.register("primary", adapter, set_as_default=True)
    yield adapter
    reset_registry()


@pytest.fixture
async def db_session(sql_adapter: SQLAlchemyAdapter) -> AsyncIterator[AsyncSession]:
    from app.infrastructure.core.context import _clear_sessions, _set_session

    async with sql_adapter.session_factory() as session:
        _set_session("primary", session)
        yield session
        _clear_sessions()


@pytest.fixture
def repo(db_session: AsyncSession) -> ItemRepository:  # noqa: ARG001
    return ItemRepository()


class TestSQLReadMixin:
    @pytest.mark.anyio
    async def test_find_by_id(self, repo: ItemRepository, db_session: AsyncSession) -> None:
        item = Item(name="Test Item")
        db_session.add(item)
        await db_session.flush()

        found = await repo.find_by_id(item.id)
        assert found is not None
        assert found.name == "Test Item"

    @pytest.mark.anyio
    async def test_find_by_id_not_found(self, repo: ItemRepository) -> None:
        found = await repo.find_by_id("nonexistent-id")
        assert found is None

    @pytest.mark.anyio
    async def test_find_by_id_excludes_deleted(
        self, repo: ItemRepository, db_session: AsyncSession
    ) -> None:
        item = Item(name="Deleted Item", is_deleted=True)
        db_session.add(item)
        await db_session.flush()

        found = await repo.find_by_id(item.id)
        assert found is None

        found_with_deleted = await repo.find_by_id(item.id, include_deleted=True)
        assert found_with_deleted is not None

    @pytest.mark.anyio
    async def test_find_all(self, repo: ItemRepository, db_session: AsyncSession) -> None:
        for i in range(5):
            db_session.add(Item(name=f"Item {i}"))
        await db_session.flush()

        items = await repo.find_all()
        assert len(items) == 5

    @pytest.mark.anyio
    async def test_find_all_with_pagination(
        self, repo: ItemRepository, db_session: AsyncSession
    ) -> None:
        for i in range(10):
            db_session.add(Item(name=f"Item {i}"))
        await db_session.flush()

        items = await repo.find_all(offset=2, limit=3)
        assert len(items) == 3

    @pytest.mark.anyio
    async def test_find_by_ids(self, repo: ItemRepository, db_session: AsyncSession) -> None:
        items = [Item(name=f"Item {i}") for i in range(5)]
        for item in items:
            db_session.add(item)
        await db_session.flush()

        ids = [items[0].id, items[2].id, items[4].id]
        found = await repo.find_by_ids(ids)
        assert len(found) == 3

    @pytest.mark.anyio
    async def test_find_by_ids_empty(self, repo: ItemRepository) -> None:
        found = await repo.find_by_ids([])
        assert found == []

    @pytest.mark.anyio
    async def test_find_where(self, repo: ItemRepository, db_session: AsyncSession) -> None:
        db_session.add(Item(name="Cat", category="animal"))
        db_session.add(Item(name="Dog", category="animal"))
        db_session.add(Item(name="Car", category="vehicle"))
        await db_session.flush()

        found = await repo.find_where(category="animal")
        assert len(found) == 2

    @pytest.mark.anyio
    async def test_exists(self, repo: ItemRepository, db_session: AsyncSession) -> None:
        item = Item(name="Existing Item")
        db_session.add(item)
        await db_session.flush()

        assert await repo.exists(item.id) is True
        assert await repo.exists("nonexistent") is False

    @pytest.mark.anyio
    async def test_count(self, repo: ItemRepository, db_session: AsyncSession) -> None:
        for i in range(7):
            db_session.add(Item(name=f"Item {i}"))
        await db_session.flush()

        count = await repo.count()
        assert count == 7


class TestSQLWriteMixin:
    @pytest.mark.anyio
    async def test_create(self, repo: ItemRepository) -> None:
        item = await repo.create({"name": "New Item", "category": "test"})

        assert item.id is not None
        assert item.name == "New Item"
        assert item.category == "test"
        assert item.created_at is not None

    @pytest.mark.anyio
    async def test_update(self, repo: ItemRepository, db_session: AsyncSession) -> None:
        item = Item(name="Original Name")
        db_session.add(item)
        await db_session.flush()

        updated = await repo.update(item.id, {"name": "Updated Name"})
        assert updated is not None
        assert updated.name == "Updated Name"

    @pytest.mark.anyio
    async def test_update_not_found(self, repo: ItemRepository) -> None:
        updated = await repo.update("nonexistent", {"name": "New Name"})
        assert updated is None

    @pytest.mark.anyio
    async def test_delete_soft(self, repo: ItemRepository, db_session: AsyncSession) -> None:
        item = Item(name="To Delete")
        db_session.add(item)
        await db_session.flush()

        deleted = await repo.delete(item.id)
        assert deleted is True

        found = await repo.find_by_id(item.id)
        assert found is None

        found_deleted = await repo.find_by_id(item.id, include_deleted=True)
        assert found_deleted is not None
        assert found_deleted.is_deleted is True

    @pytest.mark.anyio
    async def test_delete_hard(self, repo: ItemRepository, db_session: AsyncSession) -> None:
        item = Item(name="To Delete Hard")
        db_session.add(item)
        await db_session.flush()
        item_id = item.id

        deleted = await repo.delete(item_id, hard=True)
        assert deleted is True

        found = await repo.find_by_id(item_id, include_deleted=True)
        assert found is None


class TestSQLBulkMixin:
    @pytest.mark.anyio
    async def test_create_many(self, repo: ItemRepository) -> None:
        items_data: list[dict[str, object]] = [
            {"name": f"Bulk Item {i}", "category": "bulk"}
            for i in range(5)
        ]
        items = await repo.create_many(items_data)

        assert len(items) == 5
        assert all(item.category == "bulk" for item in items)

    @pytest.mark.anyio
    async def test_create_many_empty(self, repo: ItemRepository) -> None:
        items = await repo.create_many([])
        assert items == []

    @pytest.mark.anyio
    async def test_update_many(self, repo: ItemRepository, db_session: AsyncSession) -> None:
        items = [Item(name=f"Item {i}", value=0) for i in range(5)]
        for item in items:
            db_session.add(item)
        await db_session.flush()

        ids = [items[0].id, items[2].id]
        count = await repo.update_many(ids, {"value": 100})

        assert count == 2

    @pytest.mark.anyio
    async def test_delete_many_soft(
        self, repo: ItemRepository, db_session: AsyncSession
    ) -> None:
        items = [Item(name=f"Item {i}") for i in range(5)]
        for item in items:
            db_session.add(item)
        await db_session.flush()

        ids = [items[0].id, items[1].id, items[2].id]
        count = await repo.delete_many(ids)

        assert count == 3
        remaining = await repo.find_all()
        assert len(remaining) == 2

    @pytest.mark.anyio
    async def test_delete_many_hard(
        self, repo: ItemRepository, db_session: AsyncSession
    ) -> None:
        items = [Item(name=f"Item {i}") for i in range(5)]
        for item in items:
            db_session.add(item)
        await db_session.flush()

        ids = [items[0].id, items[1].id]
        count = await repo.delete_many(ids, hard=True)

        assert count == 2
        all_items = await repo.find_all(include_deleted=True)
        assert len(all_items) == 3


class TestSQLPaginationMixin:
    @pytest.mark.anyio
    async def test_find_paginated(
        self, repo: ItemRepository, db_session: AsyncSession
    ) -> None:
        for i in range(25):
            db_session.add(Item(name=f"Item {i}"))
        await db_session.flush()

        items, total = await repo.find_paginated(page=1, page_size=10)
        assert len(items) == 10
        assert total == 25

        items, total = await repo.find_paginated(page=3, page_size=10)
        assert len(items) == 5
        assert total == 25

    @pytest.mark.anyio
    async def test_find_by_cursor(
        self, repo: ItemRepository, db_session: AsyncSession
    ) -> None:
        for i in range(10):
            db_session.add(Item(name=f"Item {i}"))
        await db_session.flush()

        items = await repo.find_by_cursor(cursor=None, limit=5)
        assert len(items) <= 6


class TestSQLSoftDeleteMixin:
    @pytest.mark.anyio
    async def test_restore(self, repo: ItemRepository, db_session: AsyncSession) -> None:
        item = Item(name="Deleted Item", is_deleted=True)
        db_session.add(item)
        await db_session.flush()

        found = await repo.find_by_id(item.id)
        assert found is None

        restored = await repo.restore(item.id)
        assert restored is not None
        assert restored.is_deleted is False

        found = await repo.find_by_id(item.id)
        assert found is not None

    @pytest.mark.anyio
    async def test_restore_not_found(self, repo: ItemRepository) -> None:
        restored = await repo.restore("nonexistent")
        assert restored is None


class TestSQLUpsertMixin:
    @pytest.mark.anyio
    async def test_upsert_insert(self, repo: ItemRepository) -> None:
        item = await repo.upsert(
            data={"name": "Unique Item", "category": "upsert"},
            conflict_fields=["name"],
        )

        assert item.id is not None
        assert item.name == "Unique Item"
        assert item.category == "upsert"

    @pytest.mark.anyio
    async def test_find_or_create_creates(self, repo: ItemRepository) -> None:
        item, created = await repo.find_or_create(
            name="New Item",
            defaults={"category": "created"},
        )

        assert created is True
        assert item.name == "New Item"
        assert item.category == "created"

    @pytest.mark.anyio
    async def test_find_or_create_finds(
        self, repo: ItemRepository, db_session: AsyncSession
    ) -> None:
        existing = Item(name="Existing", category="original")
        db_session.add(existing)
        await db_session.flush()

        item, created = await repo.find_or_create(
            name="Existing",
            defaults={"category": "should_not_use"},
        )

        assert created is False
        assert item.id == existing.id
        assert item.category == "original"


class TestRepositoryWithExplicitSession:
    @pytest.mark.anyio
    async def test_explicit_session_injection(
        self, sql_adapter: SQLAlchemyAdapter
    ) -> None:
        async with sql_adapter.session_factory() as session:
            repo = ItemRepository(session=session)

            item = await repo.create({"name": "Injected Session Item"})
            assert item.id is not None

            found = await repo.find_by_id(item.id)
            assert found is not None


class TestRepositoryCustomization:
    @pytest.mark.anyio
    async def test_custom_repository_methods(
        self, sql_adapter: SQLAlchemyAdapter
    ) -> None:
        from app.infrastructure.core.context import _clear_sessions, _set_session

        class CustomItemRepository(BaseSQLRepository[Item]):
            async def find_by_category(self, category: str) -> list[Item]:
                return await self.find_where(category=category)

            async def count_by_category(self, category: str) -> int:
                items = await self.find_by_category(category)
                return len(items)

        async with sql_adapter.session_factory() as session:
            _set_session("primary", session)

            repo = CustomItemRepository()
            await repo.create({"name": "Item 1", "category": "A"})
            await repo.create({"name": "Item 2", "category": "A"})
            await repo.create({"name": "Item 3", "category": "B"})

            a_items = await repo.find_by_category("A")
            assert len(a_items) == 2

            count = await repo.count_by_category("A")
            assert count == 2

            _clear_sessions()
