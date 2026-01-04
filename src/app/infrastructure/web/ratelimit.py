from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.config import settings


def _key_func(request: Request) -> str:
    return get_remote_address(request) or "anonymous"


limiter = Limiter(
    key_func=_key_func,
    default_limits=[settings.ratelimit.default] if settings.ratelimit.enabled else [],
    enabled=settings.ratelimit.enabled,
    storage_uri=settings.databases.redis.url if settings.databases.redis.enabled else None,
)
