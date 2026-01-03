from fastapi import FastAPI, HTTPException

from app.config import settings
from app.infrastructure import AppException, get_database
from app.infrastructure.exceptions import app_exception_handler, http_exception_handler
from app.infrastructure.lifespan import lifespan
from app.infrastructure.middleware import DBSessionMiddleware
from app.router import router


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.name,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)

    app.include_router(router)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy"}

    return DBSessionMiddleware(app, get_database())  # type: ignore[return-value]


app = create_app()
