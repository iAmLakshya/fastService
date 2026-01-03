from contextvars import ContextVar

from sqlalchemy.ext.asyncio import AsyncSession

_session: ContextVar[AsyncSession | None] = ContextVar("session", default=None)


def get_db() -> AsyncSession:
    session = _session.get()
    if session is None:
        raise RuntimeError("No database session in context. Are you inside a request?")
    return session


def _set_session(session: AsyncSession) -> None:
    _session.set(session)


def _reset_session() -> None:
    _session.set(None)
