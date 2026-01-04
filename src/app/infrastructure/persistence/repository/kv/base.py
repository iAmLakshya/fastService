import json
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from app.infrastructure.persistence.adapters import RedisAdapter, get_registry
from app.infrastructure.persistence.adapters.protocols import DatabaseType

if TYPE_CHECKING:
    import redis.asyncio as aioredis

T = TypeVar("T")


class BaseKeyValueRepository(Generic[T]):
    key_prefix: str = ""
    adapter_name: str | None = None

    def __init__(self) -> None:
        self._adapter: RedisAdapter | None = None

    def _get_adapter(self) -> RedisAdapter:
        if self._adapter is None:
            registry = get_registry()
            if self.adapter_name:
                self._adapter = registry.get_typed(self.adapter_name, RedisAdapter)
            else:
                adapter = registry.get_default(DatabaseType.KEY_VALUE)
                if not isinstance(adapter, RedisAdapter):
                    raise TypeError("Default KV adapter is not RedisAdapter")
                self._adapter = adapter
        return self._adapter

    @property
    def _client(self) -> "aioredis.Redis":
        return self._get_adapter().get_connection()

    def _make_key(self, key: str) -> str:
        if self.key_prefix:
            return f"{self.key_prefix}:{key}"
        return key

    def _strip_prefix(self, key: str) -> str:
        if self.key_prefix and key.startswith(f"{self.key_prefix}:"):
            return key[len(self.key_prefix) + 1 :]
        return key

    def _serialize(self, value: T) -> str:
        return json.dumps(value, default=str)

    def _deserialize(self, value: str | None) -> T | None:
        if value is None:
            return None
        return json.loads(value)

    async def get(self, key: str) -> T | None:
        value = await self._client.get(self._make_key(key))
        return self._deserialize(value)

    async def set(self, key: str, value: T, ttl: int | None = None) -> bool:
        full_key = self._make_key(key)
        serialized = self._serialize(value)
        if ttl:
            result = await self._client.setex(full_key, ttl, serialized)
        else:
            result = await self._client.set(full_key, serialized)
        return bool(result)

    async def delete(self, key: str) -> bool:
        return await self._client.delete(self._make_key(key)) > 0

    async def exists(self, key: str) -> bool:
        return await self._client.exists(self._make_key(key)) > 0

    async def get_many(self, keys: list[str]) -> dict[str, T | None]:
        if not keys:
            return {}
        full_keys = [self._make_key(k) for k in keys]
        values = await self._client.mget(full_keys)
        return {key: self._deserialize(val) for key, val in zip(keys, values, strict=True)}

    async def set_many(self, items: dict[str, T], ttl: int | None = None) -> bool:
        if not items:
            return True
        pipe = self._client.pipeline()
        for key, value in items.items():
            full_key = self._make_key(key)
            serialized = self._serialize(value)
            if ttl:
                pipe.setex(full_key, ttl, serialized)
            else:
                pipe.set(full_key, serialized)
        await pipe.execute()
        return True

    async def delete_many(self, keys: list[str]) -> int:
        if not keys:
            return 0
        full_keys = [self._make_key(k) for k in keys]
        return await self._client.delete(*full_keys)

    async def keys(self, pattern: str = "*") -> list[str]:
        full_pattern = self._make_key(pattern)
        raw_keys = await self._client.keys(full_pattern)
        return [self._strip_prefix(k) for k in raw_keys]

    async def ttl(self, key: str) -> int | None:
        result = await self._client.ttl(self._make_key(key))
        return result if result > 0 else None

    async def expire(self, key: str, seconds: int) -> bool:
        return await self._client.expire(self._make_key(key), seconds)

    async def hget(self, key: str, field: str) -> Any:
        value = await self._client.hget(self._make_key(key), field)
        return self._deserialize(value)

    async def hset(self, key: str, field: str, value: Any) -> bool:
        result = await self._client.hset(self._make_key(key), field, self._serialize(value))
        return bool(result)

    async def hgetall(self, key: str) -> dict[str, Any]:
        data = await self._client.hgetall(self._make_key(key))
        return {k: self._deserialize(v) for k, v in data.items()}

    async def hdel(self, key: str, *fields: str) -> int:
        if not fields:
            return 0
        return await self._client.hdel(self._make_key(key), *fields)

    async def hexists(self, key: str, field: str) -> bool:
        return await self._client.hexists(self._make_key(key), field)
