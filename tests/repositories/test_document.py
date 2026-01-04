from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.infrastructure.persistence.adapters import (
    MongoAdapter,
    MongoConfig,
    get_registry,
    reset_registry,
)
from app.infrastructure.persistence.repository import BaseDocumentRepository


class ProfileRepository(BaseDocumentRepository[dict[str, Any]]):
    collection_name = "profiles"


class EventRepository(BaseDocumentRepository[dict[str, Any]]):
    collection_name = "events"


@pytest.fixture
def mock_collection() -> MagicMock:
    collection = MagicMock()
    collection.find_one = AsyncMock()
    collection.find = MagicMock()
    collection.insert_one = AsyncMock()
    collection.insert_many = AsyncMock()
    collection.update_one = AsyncMock()
    collection.update_many = AsyncMock()
    collection.delete_one = AsyncMock()
    collection.delete_many = AsyncMock()
    collection.count_documents = AsyncMock()
    collection.distinct = AsyncMock()
    collection.aggregate = MagicMock()
    collection.replace_one = AsyncMock()
    return collection


@pytest.fixture
def mock_cursor() -> MagicMock:
    cursor = MagicMock()
    cursor.sort = MagicMock(return_value=cursor)
    cursor.skip = MagicMock(return_value=cursor)
    cursor.limit = MagicMock(return_value=cursor)
    cursor.to_list = AsyncMock()
    return cursor


@pytest.fixture
async def mongo_adapter(
    mock_collection: MagicMock,
) -> AsyncIterator[MongoAdapter]:
    reset_registry()
    adapter = MongoAdapter(
        MongoConfig(url="mongodb://localhost:27017", database="test")
    )
    mock_database = MagicMock()
    mock_database.__getitem__ = MagicMock(return_value=mock_collection)
    adapter._database = mock_database
    adapter._client = MagicMock()

    registry = get_registry()
    registry.register("mongo", adapter, set_as_default=True)

    yield adapter
    reset_registry()


@pytest.fixture
def profile_repo(mongo_adapter: MongoAdapter) -> ProfileRepository:  # noqa: ARG001
    return ProfileRepository()


class TestBaseDocumentRepository:
    @pytest.mark.anyio
    async def test_find_by_id(
        self,
        profile_repo: ProfileRepository,
        mock_collection: MagicMock,
    ) -> None:
        mock_collection.find_one.return_value = {"_id": "123", "name": "John"}

        result = await profile_repo.find_by_id("123")

        assert result == {"_id": "123", "name": "John"}
        mock_collection.find_one.assert_called_once_with({"_id": "123"})

    @pytest.mark.anyio
    async def test_find_by_id_not_found(
        self,
        profile_repo: ProfileRepository,
        mock_collection: MagicMock,
    ) -> None:
        mock_collection.find_one.return_value = None

        result = await profile_repo.find_by_id("nonexistent")

        assert result is None

    @pytest.mark.anyio
    async def test_find_one(
        self,
        profile_repo: ProfileRepository,
        mock_collection: MagicMock,
    ) -> None:
        mock_collection.find_one.return_value = {"_id": "1", "email": "john@test.com"}

        result = await profile_repo.find_one({"email": "john@test.com"})

        assert result == {"_id": "1", "email": "john@test.com"}
        mock_collection.find_one.assert_called_with({"email": "john@test.com"})

    @pytest.mark.anyio
    async def test_find_many(
        self,
        profile_repo: ProfileRepository,
        mock_collection: MagicMock,
        mock_cursor: MagicMock,
    ) -> None:
        mock_collection.find.return_value = mock_cursor
        mock_cursor.to_list.return_value = [
            {"_id": "1", "name": "John"},
            {"_id": "2", "name": "Jane"},
        ]

        result = await profile_repo.find_many({"active": True}, skip=0, limit=10)

        assert len(result) == 2
        mock_collection.find.assert_called_once_with({"active": True})
        mock_cursor.skip.assert_called_once_with(0)
        mock_cursor.limit.assert_called_once_with(10)

    @pytest.mark.anyio
    async def test_find_many_with_sort(
        self,
        profile_repo: ProfileRepository,
        mock_collection: MagicMock,
        mock_cursor: MagicMock,
    ) -> None:
        mock_collection.find.return_value = mock_cursor
        mock_cursor.to_list.return_value = []

        await profile_repo.find_many(
            filter=None,
            sort=[("created_at", -1)],
        )

        mock_cursor.sort.assert_called_once_with([("created_at", -1)])

    @pytest.mark.anyio
    async def test_count_documents(
        self,
        profile_repo: ProfileRepository,
        mock_collection: MagicMock,
    ) -> None:
        mock_collection.count_documents.return_value = 42

        result = await profile_repo.count_documents({"status": "active"})

        assert result == 42
        mock_collection.count_documents.assert_called_once_with({"status": "active"})

    @pytest.mark.anyio
    async def test_count_documents_no_filter(
        self,
        profile_repo: ProfileRepository,
        mock_collection: MagicMock,
    ) -> None:
        mock_collection.count_documents.return_value = 100

        result = await profile_repo.count_documents()

        assert result == 100
        mock_collection.count_documents.assert_called_once_with({})

    @pytest.mark.anyio
    async def test_distinct(
        self,
        profile_repo: ProfileRepository,
        mock_collection: MagicMock,
    ) -> None:
        mock_collection.distinct.return_value = ["US", "UK", "CA"]

        result = await profile_repo.distinct("country", {"active": True})

        assert result == ["US", "UK", "CA"]
        mock_collection.distinct.assert_called_once_with("country", {"active": True})


class TestDocumentWriteOperations:
    @pytest.mark.anyio
    async def test_insert_one(
        self,
        profile_repo: ProfileRepository,
        mock_collection: MagicMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.inserted_id = "new_id"
        mock_collection.insert_one.return_value = mock_result
        mock_collection.find_one.return_value = {
            "_id": "new_id",
            "name": "New Profile",
        }

        result = await profile_repo.insert_one({"name": "New Profile"})

        assert result["_id"] == "new_id"
        mock_collection.insert_one.assert_called_once()

    @pytest.mark.anyio
    async def test_insert_many(
        self,
        profile_repo: ProfileRepository,
        mock_collection: MagicMock,
        mock_cursor: MagicMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.inserted_ids = ["id1", "id2", "id3"]
        mock_collection.insert_many.return_value = mock_result
        mock_collection.find.return_value = mock_cursor
        mock_cursor.to_list.return_value = [
            {"_id": "id1"},
            {"_id": "id2"},
            {"_id": "id3"},
        ]

        docs = [{"name": f"Profile {i}"} for i in range(3)]
        result = await profile_repo.insert_many(docs)

        assert len(result) == 3
        mock_collection.insert_many.assert_called_once_with(docs)

    @pytest.mark.anyio
    async def test_insert_many_empty(
        self,
        profile_repo: ProfileRepository,
        mock_collection: MagicMock,
    ) -> None:
        result = await profile_repo.insert_many([])

        assert result == []
        mock_collection.insert_many.assert_not_called()

    @pytest.mark.anyio
    async def test_update_one(
        self,
        profile_repo: ProfileRepository,
        mock_collection: MagicMock,
    ) -> None:
        mock_collection.find_one.return_value = {"_id": "1", "name": "Updated"}

        result = await profile_repo.update_one(
            {"_id": "1"},
            {"name": "Updated"},
        )

        assert result is not None
        assert result["name"] == "Updated"
        mock_collection.update_one.assert_called_once_with(
            {"_id": "1"},
            {"$set": {"name": "Updated"}},
            upsert=False,
        )

    @pytest.mark.anyio
    async def test_update_one_with_upsert(
        self,
        profile_repo: ProfileRepository,
        mock_collection: MagicMock,
    ) -> None:
        mock_collection.find_one.return_value = {"_id": "1", "name": "Upserted"}

        await profile_repo.update_one(
            {"external_id": "ext123"},
            {"name": "Upserted"},
            upsert=True,
        )

        mock_collection.update_one.assert_called_once_with(
            {"external_id": "ext123"},
            {"$set": {"name": "Upserted"}},
            upsert=True,
        )

    @pytest.mark.anyio
    async def test_update_many(
        self,
        profile_repo: ProfileRepository,
        mock_collection: MagicMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.modified_count = 5
        mock_collection.update_many.return_value = mock_result

        count = await profile_repo.update_many(
            {"status": "pending"},
            {"status": "processed"},
        )

        assert count == 5

    @pytest.mark.anyio
    async def test_delete_one(
        self,
        profile_repo: ProfileRepository,
        mock_collection: MagicMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_collection.delete_one.return_value = mock_result

        result = await profile_repo.delete_one({"_id": "123"})

        assert result is True
        mock_collection.delete_one.assert_called_once_with({"_id": "123"})

    @pytest.mark.anyio
    async def test_delete_one_not_found(
        self,
        profile_repo: ProfileRepository,
        mock_collection: MagicMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.deleted_count = 0
        mock_collection.delete_one.return_value = mock_result

        result = await profile_repo.delete_one({"_id": "nonexistent"})

        assert result is False

    @pytest.mark.anyio
    async def test_delete_many(
        self,
        profile_repo: ProfileRepository,
        mock_collection: MagicMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.deleted_count = 10
        mock_collection.delete_many.return_value = mock_result

        count = await profile_repo.delete_many({"expired": True})

        assert count == 10

    @pytest.mark.anyio
    async def test_replace_one(
        self,
        profile_repo: ProfileRepository,
        mock_collection: MagicMock,
    ) -> None:
        replacement = {"_id": "1", "name": "Replaced", "version": 2}
        mock_collection.find_one.return_value = replacement

        result = await profile_repo.replace_one(
            {"_id": "1"},
            replacement,
        )

        assert result == replacement
        mock_collection.replace_one.assert_called_once_with(
            {"_id": "1"},
            replacement,
            upsert=False,
        )


class TestDocumentAggregation:
    @pytest.mark.anyio
    async def test_aggregate(
        self,
        profile_repo: ProfileRepository,
        mock_collection: MagicMock,
    ) -> None:
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(
            return_value=[
                {"_id": "US", "count": 100},
                {"_id": "UK", "count": 50},
            ]
        )
        mock_collection.aggregate.return_value = mock_cursor

        pipeline: list[dict[str, Any]] = [
            {"$group": {"_id": "$country", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        result = await profile_repo.aggregate(pipeline)

        assert len(result) == 2
        assert result[0]["count"] == 100
        mock_collection.aggregate.assert_called_once_with(pipeline)


class TestCustomDocumentRepository:
    @pytest.mark.anyio
    async def test_custom_repository_methods(
        self,
        mongo_adapter: MongoAdapter,  # noqa: ARG002
        mock_collection: MagicMock,
        mock_cursor: MagicMock,  # noqa: ARG002
    ) -> None:
        class UserRepository(BaseDocumentRepository[dict[str, Any]]):
            collection_name = "users"

            async def find_by_email(self, email: str) -> dict[str, Any] | None:
                return await self.find_one({"email": email})

            async def find_active_users(
                self, limit: int = 100
            ) -> list[dict[str, Any]]:
                return await self.find_many(
                    {"status": "active"},
                    sort=[("last_login", -1)],
                    limit=limit,
                )

            async def deactivate_users(
                self, user_ids: list[str]
            ) -> int:
                return await self.update_many(
                    {"_id": {"$in": user_ids}},
                    {"status": "inactive"},
                )

        mock_collection.find_one.return_value = {
            "_id": "1",
            "email": "test@example.com",
        }

        repo = UserRepository()
        user = await repo.find_by_email("test@example.com")

        assert user is not None
        assert user["email"] == "test@example.com"


class TestRepositoryWithDifferentAdapters:
    @pytest.mark.anyio
    async def test_named_adapter(
        self,
        mock_collection: MagicMock,
    ) -> None:
        reset_registry()

        class AnalyticsRepository(BaseDocumentRepository[dict[str, Any]]):
            collection_name = "events"
            adapter_name = "analytics_db"

        adapter = MongoAdapter(
            MongoConfig(url="mongodb://localhost:27017", database="analytics")
        )
        mock_database = MagicMock()
        mock_database.__getitem__ = MagicMock(return_value=mock_collection)
        adapter._database = mock_database
        adapter._client = MagicMock()

        registry = get_registry()
        registry.register("analytics_db", adapter)

        mock_collection.find_one.return_value = {"_id": "event1", "type": "click"}

        repo = AnalyticsRepository()
        event = await repo.find_by_id("event1")

        assert event is not None
        assert event["type"] == "click"

        reset_registry()
