from sqlalchemy import select

from app.infrastructure import BaseRepository
from app.modules.todos.model import Todo


class TodoRepository(BaseRepository[Todo]):
    model = Todo

    async def get_by_completed_status(
        self, completed: bool, skip: int = 0, limit: int = 100
    ) -> list[Todo]:
        stmt = (
            select(Todo)
            .where(Todo.completed == completed)
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
