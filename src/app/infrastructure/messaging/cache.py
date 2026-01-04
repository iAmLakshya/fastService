import hashlib
import json
from collections.abc import Awaitable, Callable
from datetime import date, datetime
from functools import wraps
from typing import Any, ParamSpec, TypeVar
from uuid import UUID

import redis.asyncio as redis

from app.config import settings
from app.infrastructure.constants import Cache

Params = ParamSpec("Params")
ReturnType = TypeVar("ReturnType")

_redis_client: redis.Redis | None = None


def _json_encoder(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return {"__type__": "datetime", "value": obj.isoformat()}
    if isinstance(obj, date):
        return {"__type__": "date", "value": obj.isoformat()}
    if isinstance(obj, UUID):
        return {"__type__": "uuid", "value": str(obj)}
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _json_decoder(obj: dict[str, Any]) -> Any:
    if "__type__" in obj:
        type_name = obj["__type__"]
        if type_name == "datetime":
            return datetime.fromisoformat(obj["value"])
        if type_name == "date":
            return date.fromisoformat(obj["value"])
        if type_name == "uuid":
            return UUID(obj["value"])
    return obj


async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        redis_config = settings.databases.redis
        _redis_client = redis.from_url(  # type: ignore[no-untyped-call]
            redis_config.url,
            encoding="utf-8",
            decode_responses=redis_config.decode_responses,
        )
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


def build_cache_key(key_prefix: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    key_hash = hashlib.sha256(key_data.encode()).hexdigest()[: Cache.KEY_HASH_LENGTH]
    return f"{key_prefix}:{key_hash}"


AsyncFunc = Callable[Params, Awaitable[ReturnType]]


def cached(
    ttl_seconds: int = Cache.DEFAULT_TTL_SECONDS,
    key_prefix: str | None = None,
) -> Callable[[AsyncFunc[Params, ReturnType]], AsyncFunc[Params, ReturnType]]:
    def decorator(func: AsyncFunc[Params, ReturnType]) -> AsyncFunc[Params, ReturnType]:
        prefix = key_prefix or func.__name__

        @wraps(func)
        async def wrapper(*args: Params.args, **kwargs: Params.kwargs) -> ReturnType:
            if not settings.databases.redis.enabled:
                return await func(*args, **kwargs)

            client = await get_redis()
            cache_key = build_cache_key(prefix, args, kwargs)

            cached_value = await client.get(cache_key)
            if cached_value is not None:
                return json.loads(cached_value, object_hook=_json_decoder)  # type: ignore[no-any-return]

            result = await func(*args, **kwargs)
            await client.setex(cache_key, ttl_seconds, json.dumps(result, default=_json_encoder))
            return result

        return wrapper

    return decorator


async def invalidate_cache(pattern: str) -> int:
    if not settings.databases.redis.enabled:
        return 0

    client = await get_redis()
    keys_to_delete: list[str] = []

    async for key in client.scan_iter(match=pattern):
        keys_to_delete.append(key)

    if keys_to_delete:
        deleted: int = await client.delete(*keys_to_delete)
        return deleted
    return 0
