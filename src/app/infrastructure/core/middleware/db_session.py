import logging
import sys
from typing import Any

from starlette.types import ASGIApp, Receive, Scope, Send

from app.infrastructure.core.context import _clear_sessions, _remove_session, _set_session
from app.infrastructure.persistence.adapters import SQLAlchemyAdapter, get_registry

logger = logging.getLogger(__name__)


class DBSessionMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        registry = get_registry()
        context_managers: dict[str, Any] = {}

        try:
            for name, adapter in registry:
                if isinstance(adapter, SQLAlchemyAdapter):
                    cm = adapter.session()
                    session = await cm.__aenter__()
                    context_managers[name] = cm
                    _set_session(name, session)

            await self.app(scope, receive, send)

        finally:
            exc_info = sys.exc_info()
            for name in reversed(list(context_managers.keys())):
                try:
                    await context_managers[name].__aexit__(*exc_info)
                except Exception:
                    logger.exception("Failed to close database session '%s'", name)
                finally:
                    _remove_session(name)

            _clear_sessions()
