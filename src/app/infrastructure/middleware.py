from collections.abc import Callable

from app.infrastructure.context import _reset_session, _set_session
from app.infrastructure.database import Database


class DBSessionMiddleware:
    def __init__(self, app: Callable, db: Database) -> None:
        self.app = app
        self.db = db

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async with self.db.session() as session:
            _set_session(session)
            try:
                await self.app(scope, receive, send)
            finally:
                _reset_session()
