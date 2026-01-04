from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.infrastructure.persistence.adapters.protocols import DatabaseType

if TYPE_CHECKING:
    import redis.asyncio as aioredis


@dataclass(frozen=True)
class RedisConfig:
    url: str
    decode_responses: bool = True
    max_connections: int = 10


class RedisAdapter:
    def __init__(self, config: RedisConfig) -> None:
        self._config = config
        self._client: aioredis.Redis | None = None

    @property
    def database_type(self) -> DatabaseType:
        return DatabaseType.KEY_VALUE

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    @property
    def config(self) -> RedisConfig:
        return self._config

    async def connect(self) -> None:
        if self._client is not None:
            return
        try:
            import redis.asyncio as aioredis
        except ImportError as e:
            raise ImportError("redis is required for Redis support: pip install redis") from e
        self._client = aioredis.from_url(  # type: ignore[no-untyped-call]
            self._config.url,
            decode_responses=self._config.decode_responses,
            max_connections=self._config.max_connections,
        )

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def dispose(self) -> None:
        await self.disconnect()

    async def health_check(self) -> bool:
        if not self.is_connected or self._client is None:
            return False
        try:
            await self._client.ping()
            return True
        except Exception:
            return False

    def get_connection(self) -> "aioredis.Redis":
        if self._client is None:
            raise RuntimeError("Adapter not connected")
        return self._client
