from app.infrastructure.core.context import get_db
from app.infrastructure.core.health import router as health_router
from app.infrastructure.core.lifespan import lifespan
from app.infrastructure.core.middleware import (
    DBSessionMiddleware,
    RequestIdMiddleware,
    RequestLoggingMiddleware,
)
from app.infrastructure.core.setup import (
    create_base_app,
    register_cors,
    register_exception_handlers,
    register_health_routes,
    register_middleware,
)

__all__ = [
    "DBSessionMiddleware",
    "RequestIdMiddleware",
    "RequestLoggingMiddleware",
    "create_base_app",
    "get_db",
    "health_router",
    "lifespan",
    "register_cors",
    "register_exception_handlers",
    "register_health_routes",
    "register_middleware",
]
