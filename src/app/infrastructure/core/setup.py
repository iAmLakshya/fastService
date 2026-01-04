from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.infrastructure.core.health import router as health_router
from app.infrastructure.core.lifespan import lifespan
from app.infrastructure.core.middleware import (
    DBSessionMiddleware,
    RequestIdMiddleware,
    RequestLoggingMiddleware,
)
from app.infrastructure.observability.logging import configure_logging
from app.infrastructure.web.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.infrastructure.web.ratelimit import limiter


def create_base_app() -> FastAPI:
    configure_logging(
        json_logs=settings.logging.json_format,
        log_level=settings.logging.level,
    )

    return FastAPI(
        title=settings.name,
        version=settings.version,
        description=settings.description,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]


def register_cors(app: FastAPI) -> None:
    if not settings.cors.enabled:
        return

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.origins,
        allow_credentials=settings.cors.allow_credentials,
        allow_methods=settings.cors.allow_methods,
        allow_headers=settings.cors.allow_headers,
    )


def register_middleware(app: FastAPI) -> None:
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(DBSessionMiddleware)
    app.add_middleware(RequestIdMiddleware)


def register_health_routes(app: FastAPI) -> None:
    app.include_router(health_router)
