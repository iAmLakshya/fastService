from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.infrastructure.persistence.adapters import (
    RedisAdapter,
    RedisConfig,
    get_registry,
    reset_registry,
)
from app.infrastructure.persistence.repository import BaseKeyValueRepository


class CacheRepository(BaseKeyValueRepository[dict[str, Any]]):
    key_prefix = "cache"


class SessionRepository(BaseKeyValueRepository[dict[str, Any]]):
    key_prefix = "session"


@pytest.fixture
async def redis_client() -> AsyncIterator[Any]:
    import fakeredis.aioredis

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.flushall()
    await client.aclose()


@pytest.fixture
async def redis_adapter(redis_client: Any) -> AsyncIterator[RedisAdapter]:
    reset_registry()
    adapter = RedisAdapter(RedisConfig(url="redis://localhost:6379/0"))
    adapter._client = redis_client
    registry = get_registry()
    registry.register("redis", adapter, set_as_default=True)
    yield adapter
    reset_registry()


@pytest.fixture
def cache_repo(redis_adapter: RedisAdapter) -> CacheRepository:  # noqa: ARG001
    return CacheRepository()


@pytest.fixture
def session_repo(redis_adapter: RedisAdapter) -> SessionRepository:  # noqa: ARG001
    return SessionRepository()


class TestBaseKeyValueRepository:
    @pytest.mark.anyio
    async def test_set_and_get(self, cache_repo: CacheRepository) -> None:
        await cache_repo.set("user:1", {"name": "John", "age": 30})
        result = await cache_repo.get("user:1")

        assert result == {"name": "John", "age": 30}

    @pytest.mark.anyio
    async def test_get_not_found(self, cache_repo: CacheRepository) -> None:
        result = await cache_repo.get("nonexistent")
        assert result is None

    @pytest.mark.anyio
    async def test_set_with_ttl(self, cache_repo: CacheRepository) -> None:
        await cache_repo.set("temp", {"data": "temporary"}, ttl=60)
        result = await cache_repo.get("temp")
        assert result == {"data": "temporary"}

        ttl = await cache_repo.ttl("temp")
        assert ttl is not None
        assert ttl > 0
        assert ttl <= 60

    @pytest.mark.anyio
    async def test_delete(self, cache_repo: CacheRepository) -> None:
        await cache_repo.set("to_delete", {"data": "value"})
        assert await cache_repo.exists("to_delete") is True

        deleted = await cache_repo.delete("to_delete")
        assert deleted is True
        assert await cache_repo.exists("to_delete") is False

    @pytest.mark.anyio
    async def test_delete_nonexistent(self, cache_repo: CacheRepository) -> None:
        deleted = await cache_repo.delete("nonexistent")
        assert deleted is False

    @pytest.mark.anyio
    async def test_exists(self, cache_repo: CacheRepository) -> None:
        assert await cache_repo.exists("key") is False
        await cache_repo.set("key", {"value": 1})
        assert await cache_repo.exists("key") is True

    @pytest.mark.anyio
    async def test_key_prefix(self, cache_repo: CacheRepository) -> None:
        full_key = cache_repo._make_key("mykey")
        assert full_key == "cache:mykey"

        stripped = cache_repo._strip_prefix("cache:mykey")
        assert stripped == "mykey"


class TestBulkOperations:
    @pytest.mark.anyio
    async def test_get_many(self, cache_repo: CacheRepository) -> None:
        await cache_repo.set("item1", {"id": 1})
        await cache_repo.set("item2", {"id": 2})
        await cache_repo.set("item3", {"id": 3})

        results = await cache_repo.get_many(["item1", "item2", "item3", "item4"])

        assert results["item1"] == {"id": 1}
        assert results["item2"] == {"id": 2}
        assert results["item3"] == {"id": 3}
        assert results["item4"] is None

    @pytest.mark.anyio
    async def test_get_many_empty(self, cache_repo: CacheRepository) -> None:
        results = await cache_repo.get_many([])
        assert results == {}

    @pytest.mark.anyio
    async def test_set_many(self, cache_repo: CacheRepository) -> None:
        items = {
            "bulk1": {"name": "Item 1"},
            "bulk2": {"name": "Item 2"},
            "bulk3": {"name": "Item 3"},
        }
        result = await cache_repo.set_many(items)
        assert result is True

        for key in items:
            value = await cache_repo.get(key)
            assert value == items[key]

    @pytest.mark.anyio
    async def test_set_many_with_ttl(self, cache_repo: CacheRepository) -> None:
        items = {"temp1": {"data": 1}, "temp2": {"data": 2}}
        await cache_repo.set_many(items, ttl=120)

        for key in items:
            ttl = await cache_repo.ttl(key)
            assert ttl is not None
            assert ttl > 0

    @pytest.mark.anyio
    async def test_set_many_empty(self, cache_repo: CacheRepository) -> None:
        result = await cache_repo.set_many({})
        assert result is True

    @pytest.mark.anyio
    async def test_delete_many(self, cache_repo: CacheRepository) -> None:
        await cache_repo.set("del1", {"id": 1})
        await cache_repo.set("del2", {"id": 2})
        await cache_repo.set("del3", {"id": 3})

        count = await cache_repo.delete_many(["del1", "del2"])
        assert count == 2

        assert await cache_repo.exists("del1") is False
        assert await cache_repo.exists("del2") is False
        assert await cache_repo.exists("del3") is True

    @pytest.mark.anyio
    async def test_delete_many_empty(self, cache_repo: CacheRepository) -> None:
        count = await cache_repo.delete_many([])
        assert count == 0


class TestKeyPatterns:
    @pytest.mark.anyio
    async def test_keys_pattern(self, cache_repo: CacheRepository) -> None:
        await cache_repo.set("user:1", {"id": 1})
        await cache_repo.set("user:2", {"id": 2})
        await cache_repo.set("product:1", {"id": 1})

        user_keys = await cache_repo.keys("user:*")
        assert len(user_keys) == 2
        assert "user:1" in user_keys
        assert "user:2" in user_keys

    @pytest.mark.anyio
    async def test_keys_all(self, cache_repo: CacheRepository) -> None:
        await cache_repo.set("a", {"v": 1})
        await cache_repo.set("b", {"v": 2})
        await cache_repo.set("c", {"v": 3})

        all_keys = await cache_repo.keys()
        assert len(all_keys) == 3


class TestTTLOperations:
    @pytest.mark.anyio
    async def test_ttl_no_expiry(self, cache_repo: CacheRepository) -> None:
        await cache_repo.set("permanent", {"data": "value"})
        ttl = await cache_repo.ttl("permanent")
        assert ttl is None

    @pytest.mark.anyio
    async def test_ttl_nonexistent(self, cache_repo: CacheRepository) -> None:
        ttl = await cache_repo.ttl("nonexistent")
        assert ttl is None

    @pytest.mark.anyio
    async def test_expire(self, cache_repo: CacheRepository) -> None:
        await cache_repo.set("to_expire", {"data": "value"})
        result = await cache_repo.expire("to_expire", 300)
        assert result is True

        ttl = await cache_repo.ttl("to_expire")
        assert ttl is not None
        assert ttl > 0


class TestHashOperations:
    @pytest.mark.anyio
    async def test_hset_and_hget(self, cache_repo: CacheRepository) -> None:
        await cache_repo.hset("user:profile", "name", "John")
        result = await cache_repo.hget("user:profile", "name")
        assert result == "John"

    @pytest.mark.anyio
    async def test_hget_not_found(self, cache_repo: CacheRepository) -> None:
        result = await cache_repo.hget("nonexistent", "field")
        assert result is None

    @pytest.mark.anyio
    async def test_hgetall(self, cache_repo: CacheRepository) -> None:
        await cache_repo.hset("profile", "name", "John")
        await cache_repo.hset("profile", "email", "john@example.com")
        await cache_repo.hset("profile", "age", 30)

        result = await cache_repo.hgetall("profile")
        assert result["name"] == "John"
        assert result["email"] == "john@example.com"
        assert result["age"] == 30

    @pytest.mark.anyio
    async def test_hdel(self, cache_repo: CacheRepository) -> None:
        await cache_repo.hset("profile", "name", "John")
        await cache_repo.hset("profile", "email", "john@example.com")

        count = await cache_repo.hdel("profile", "name")
        assert count == 1

        result = await cache_repo.hget("profile", "name")
        assert result is None

        result = await cache_repo.hget("profile", "email")
        assert result == "john@example.com"

    @pytest.mark.anyio
    async def test_hdel_empty(self, cache_repo: CacheRepository) -> None:
        count = await cache_repo.hdel("profile")
        assert count == 0

    @pytest.mark.anyio
    async def test_hexists(self, cache_repo: CacheRepository) -> None:
        await cache_repo.hset("profile", "name", "John")

        assert await cache_repo.hexists("profile", "name") is True
        assert await cache_repo.hexists("profile", "nonexistent") is False


class TestMultipleRepositories:
    @pytest.mark.anyio
    async def test_different_prefixes_isolated(
        self, cache_repo: CacheRepository, session_repo: SessionRepository
    ) -> None:
        await cache_repo.set("data", {"type": "cache"})
        await session_repo.set("data", {"type": "session"})

        cache_data = await cache_repo.get("data")
        session_data = await session_repo.get("data")

        assert cache_data == {"type": "cache"}
        assert session_data == {"type": "session"}


class TestCustomRepository:
    @pytest.mark.anyio
    async def test_custom_serialization(self, redis_adapter: RedisAdapter) -> None:  # noqa: ARG002
        class UserSession(BaseKeyValueRepository[dict[str, Any]]):
            key_prefix = "user_session"

            async def create_session(
                self, user_id: str, data: dict[str, Any], ttl: int = 3600
            ) -> bool:
                return await self.set(f"user:{user_id}", data, ttl=ttl)

            async def get_session(self, user_id: str) -> dict[str, Any] | None:
                return await self.get(f"user:{user_id}")

            async def invalidate_session(self, user_id: str) -> bool:
                return await self.delete(f"user:{user_id}")

        repo = UserSession()

        await repo.create_session("123", {"logged_in": True, "roles": ["admin"]})
        session = await repo.get_session("123")

        assert session is not None
        assert session["logged_in"] is True
        assert "admin" in session["roles"]

        await repo.invalidate_session("123")
        session = await repo.get_session("123")
        assert session is None
