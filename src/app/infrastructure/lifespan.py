from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.infrastructure.database import get_database


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    db = get_database()
    await db.create_tables()
    yield
    await db.close()
