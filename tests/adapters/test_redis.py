from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.persistence.adapters import RedisAdapter, RedisConfig
from app.infrastructure.persistence.adapters.protocols import DatabaseType


class TestRedisConfig:
    def test_default_values(self) -> None:
        config = RedisConfig(url="redis://localhost:6379/0")
        assert config.decode_responses is True
        assert config.max_connections == 10

    def test_custom_values(self) -> None:
        config = RedisConfig(
            url="redis://user:pass@localhost:6379/1",
            decode_responses=False,
            max_connections=50,
        )
        assert config.url == "redis://user:pass@localhost:6379/1"
        assert config.decode_responses is False
        assert config.max_connections == 50

    def test_immutable(self) -> None:
        config = RedisConfig(url="redis://localhost:6379/0")
        with pytest.raises(AttributeError):
            config.url = "redis://new"


class TestRedisAdapter:
    @pytest.fixture
    def config(self) -> RedisConfig:
        return RedisConfig(url="redis://localhost:6379/0")

    @pytest.fixture
    def adapter(self, config: RedisConfig) -> RedisAdapter:
        return RedisAdapter(config)

    def test_initial_state(self, adapter: RedisAdapter) -> None:
        assert adapter.database_type == DatabaseType.KEY_VALUE
        assert adapter.is_connected is False
        assert adapter.config.url == "redis://localhost:6379/0"

    @pytest.mark.anyio
    async def test_connect_with_fakeredis(self, adapter: RedisAdapter) -> None:
        import fakeredis.aioredis

        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
            mock_from_url.return_value = mock_client

            await adapter.connect()
            assert adapter.is_connected is True
            assert adapter._client is mock_client

            await adapter.disconnect()

    @pytest.mark.anyio
    async def test_connect_idempotent(self, adapter: RedisAdapter) -> None:
        import fakeredis.aioredis

        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
            mock_from_url.return_value = mock_client

            await adapter.connect()
            client1 = adapter._client
            await adapter.connect()
            client2 = adapter._client
            assert client1 is client2

            await adapter.disconnect()

    @pytest.mark.anyio
    async def test_disconnect(self, adapter: RedisAdapter) -> None:
        mock_client = AsyncMock()
        adapter._client = mock_client

        await adapter.disconnect()
        assert adapter.is_connected is False
        mock_client.aclose.assert_called_once()

    @pytest.mark.anyio
    async def test_health_check_connected(self, adapter: RedisAdapter) -> None:
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=True)
        adapter._client = mock_client

        result = await adapter.health_check()
        assert result is True
        mock_client.ping.assert_called_once()

    @pytest.mark.anyio
    async def test_health_check_not_connected(self, adapter: RedisAdapter) -> None:
        result = await adapter.health_check()
        assert result is False

    @pytest.mark.anyio
    async def test_health_check_ping_fails(self, adapter: RedisAdapter) -> None:
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(side_effect=Exception("Connection refused"))
        adapter._client = mock_client

        result = await adapter.health_check()
        assert result is False

    def test_get_connection(self, adapter: RedisAdapter) -> None:
        mock_client = MagicMock()
        adapter._client = mock_client

        result = adapter.get_connection()
        assert result is mock_client

    def test_get_connection_raises_when_not_connected(
        self, adapter: RedisAdapter
    ) -> None:
        with pytest.raises(RuntimeError, match="Adapter not connected"):
            adapter.get_connection()


class TestRedisAdapterIntegration:
    @pytest.fixture
    async def redis_client(self) -> AsyncIterator[Any]:
        import fakeredis.aioredis

        client = fakeredis.aioredis.FakeRedis(decode_responses=True)
        yield client
        await client.flushall()
        await client.aclose()

    @pytest.fixture
    def adapter_with_fake(self, redis_client: Any) -> RedisAdapter:
        adapter = RedisAdapter(RedisConfig(url="redis://localhost:6379/0"))
        adapter._client = redis_client
        return adapter

    @pytest.mark.anyio
    async def test_basic_operations(self, adapter_with_fake: RedisAdapter) -> None:
        client = adapter_with_fake.get_connection()

        await client.set("test_key", "test_value")
        result = await client.get("test_key")
        assert result == "test_value"

        await client.delete("test_key")
        result = await client.get("test_key")
        assert result is None

    @pytest.mark.anyio
    async def test_hash_operations(self, adapter_with_fake: RedisAdapter) -> None:
        client = adapter_with_fake.get_connection()

        await client.hset("user:1", mapping={"name": "John", "email": "john@example.com"})
        result = await client.hgetall("user:1")
        assert result == {"name": "John", "email": "john@example.com"}

        name = await client.hget("user:1", "name")
        assert name == "John"

    @pytest.mark.anyio
    async def test_list_operations(self, adapter_with_fake: RedisAdapter) -> None:
        client = adapter_with_fake.get_connection()

        await client.rpush("queue", "item1", "item2", "item3")
        length = await client.llen("queue")
        assert length == 3

        item = await client.lpop("queue")
        assert item == "item1"

    @pytest.mark.anyio
    async def test_set_operations(self, adapter_with_fake: RedisAdapter) -> None:
        client = adapter_with_fake.get_connection()

        await client.sadd("tags", "python", "fastapi", "redis")
        members = await client.smembers("tags")
        assert members == {"python", "fastapi", "redis"}

        is_member = await client.sismember("tags", "python")
        assert is_member

    @pytest.mark.anyio
    async def test_expiry(self, adapter_with_fake: RedisAdapter) -> None:
        client = adapter_with_fake.get_connection()

        await client.setex("temp_key", 60, "temp_value")
        ttl = await client.ttl("temp_key")
        assert ttl > 0
        assert ttl <= 60
