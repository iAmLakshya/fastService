from unittest.mock import AsyncMock, MagicMock

import pytest

from app.infrastructure.persistence.adapters import MongoAdapter, MongoConfig
from app.infrastructure.persistence.adapters.protocols import DatabaseType


class TestMongoConfig:
    def test_default_values(self) -> None:
        config = MongoConfig(url="mongodb://localhost:27017", database="test")
        assert config.max_pool_size == 100
        assert config.min_pool_size == 0

    def test_custom_values(self) -> None:
        config = MongoConfig(
            url="mongodb://user:pass@localhost:27017",
            database="mydb",
            max_pool_size=50,
            min_pool_size=10,
        )
        assert config.url == "mongodb://user:pass@localhost:27017"
        assert config.database == "mydb"
        assert config.max_pool_size == 50
        assert config.min_pool_size == 10

    def test_immutable(self) -> None:
        config = MongoConfig(url="mongodb://localhost:27017", database="test")
        with pytest.raises(AttributeError):
            config.url = "mongodb://new"  # type: ignore[misc]


class TestMongoAdapter:
    @pytest.fixture
    def config(self) -> MongoConfig:
        return MongoConfig(url="mongodb://localhost:27017", database="test_db")

    @pytest.fixture
    def adapter(self, config: MongoConfig) -> MongoAdapter:
        return MongoAdapter(config)

    def test_initial_state(self, adapter: MongoAdapter) -> None:
        assert adapter.database_type == DatabaseType.DOCUMENT
        assert adapter.is_connected is False
        assert adapter.config.database == "test_db"

    def test_connected_after_manual_setup(self, adapter: MongoAdapter) -> None:
        mock_client = MagicMock()
        mock_database = MagicMock()
        adapter._client = mock_client
        adapter._database = mock_database
        assert adapter.is_connected is True

    @pytest.mark.anyio
    async def test_disconnect(self, adapter: MongoAdapter) -> None:
        mock_client = MagicMock()
        adapter._client = mock_client
        adapter._database = MagicMock()

        await adapter.disconnect()
        assert adapter.is_connected is False
        mock_client.close.assert_called_once()

    @pytest.mark.anyio
    async def test_health_check_connected(self, adapter: MongoAdapter) -> None:
        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})
        adapter._client = mock_client
        adapter._database = MagicMock()

        result = await adapter.health_check()
        assert result is True
        mock_client.admin.command.assert_called_once_with("ping")

    @pytest.mark.anyio
    async def test_health_check_not_connected(self, adapter: MongoAdapter) -> None:
        result = await adapter.health_check()
        assert result is False

    @pytest.mark.anyio
    async def test_health_check_ping_fails(self, adapter: MongoAdapter) -> None:
        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock(side_effect=Exception("Connection refused"))
        adapter._client = mock_client
        adapter._database = MagicMock()

        result = await adapter.health_check()
        assert result is False

    def test_get_connection(self, adapter: MongoAdapter) -> None:
        mock_database = MagicMock()
        adapter._database = mock_database

        result = adapter.get_connection()
        assert result is mock_database

    def test_get_connection_raises_when_not_connected(
        self, adapter: MongoAdapter
    ) -> None:
        with pytest.raises(RuntimeError, match="Adapter not connected"):
            adapter.get_connection()

    def test_collection(self, adapter: MongoAdapter) -> None:
        mock_database = MagicMock()
        mock_collection = MagicMock()
        mock_database.__getitem__ = MagicMock(return_value=mock_collection)
        adapter._database = mock_database

        result = adapter.collection("users")
        assert result is mock_collection
        mock_database.__getitem__.assert_called_once_with("users")


class TestMongoAdapterWithMockedCollection:
    @pytest.fixture
    def mock_collection(self) -> MagicMock:
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
        collection.aggregate = MagicMock()
        return collection

    @pytest.fixture
    def adapter_with_mock(self, mock_collection: MagicMock) -> MongoAdapter:
        adapter = MongoAdapter(
            MongoConfig(url="mongodb://localhost:27017", database="test")
        )
        mock_database = MagicMock()
        mock_database.__getitem__ = MagicMock(return_value=mock_collection)
        adapter._database = mock_database
        adapter._client = MagicMock()
        return adapter

    @pytest.mark.anyio
    async def test_find_one(
        self, adapter_with_mock: MongoAdapter, mock_collection: MagicMock
    ) -> None:
        mock_collection.find_one.return_value = {"_id": "1", "name": "test"}

        collection = adapter_with_mock.collection("test")
        result = await collection.find_one({"_id": "1"})

        assert result == {"_id": "1", "name": "test"}
        mock_collection.find_one.assert_called_once_with({"_id": "1"})

    @pytest.mark.anyio
    async def test_insert_one(
        self, adapter_with_mock: MongoAdapter, mock_collection: MagicMock
    ) -> None:
        mock_result = MagicMock()
        mock_result.inserted_id = "123"
        mock_collection.insert_one.return_value = mock_result

        collection = adapter_with_mock.collection("test")
        result = await collection.insert_one({"name": "new item"})

        assert result.inserted_id == "123"

    @pytest.mark.anyio
    async def test_update_one(
        self, adapter_with_mock: MongoAdapter, mock_collection: MagicMock
    ) -> None:
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_collection.update_one.return_value = mock_result

        collection = adapter_with_mock.collection("test")
        result = await collection.update_one(
            {"_id": "1"}, {"$set": {"name": "updated"}}
        )

        assert result.modified_count == 1

    @pytest.mark.anyio
    async def test_delete_one(
        self, adapter_with_mock: MongoAdapter, mock_collection: MagicMock
    ) -> None:
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_collection.delete_one.return_value = mock_result

        collection = adapter_with_mock.collection("test")
        result = await collection.delete_one({"_id": "1"})

        assert result.deleted_count == 1

    @pytest.mark.anyio
    async def test_count_documents(
        self, adapter_with_mock: MongoAdapter, mock_collection: MagicMock
    ) -> None:
        mock_collection.count_documents.return_value = 42

        collection = adapter_with_mock.collection("test")
        result = await collection.count_documents({})

        assert result == 42
