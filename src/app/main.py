from fastapi import FastAPI

from app.infrastructure.core.setup import (
    create_base_app,
    register_cors,
    register_exception_handlers,
    register_health_routes,
    register_middleware,
)
from app.router import router


def create_app() -> FastAPI:
    app = create_base_app()

    register_exception_handlers(app)
    register_cors(app)
    register_middleware(app)

    register_health_routes(app)
    app.include_router(router)

    return app


app = create_app()
