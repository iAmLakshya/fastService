from contextvars import ContextVar
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

_sessions: ContextVar[dict[str, Any] | None] = ContextVar("db_sessions", default=None)

DEFAULT_SESSION_NAME = "primary"


class NoSessionError(RuntimeError):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(
            f"No database session for '{name}' in context. "
            "Are you inside a request with the database middleware configured?"
        )


def get_db(name: str = DEFAULT_SESSION_NAME) -> AsyncSession:
    sessions = _sessions.get() or {}
    if name not in sessions:
        raise NoSessionError(name)
    return cast(AsyncSession, sessions[name])


def _set_session(name: str, session: Any) -> None:
    sessions = (_sessions.get() or {}).copy()
    sessions[name] = session
    _sessions.set(sessions)


def _remove_session(name: str) -> None:
    sessions = (_sessions.get() or {}).copy()
    sessions.pop(name, None)
    _sessions.set(sessions)


def _clear_sessions() -> None:
    _sessions.set(None)


def _get_all_sessions() -> dict[str, Any]:
    return (_sessions.get() or {}).copy()
