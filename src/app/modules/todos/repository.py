from sqlalchemy import func, select

from app.infrastructure.constants import Pagination
from app.infrastructure.persistence.repository.sql import BaseSQLRepository
from app.infrastructure.persistence.repository.sql.mixins import _exclude_deleted
from app.modules.todos.model import Todo


class TodoRepository(BaseSQLRepository[Todo]):
    async def find_by_status(
        self,
        completed: bool,
        offset: int = 0,
        limit: int = Pagination.DEFAULT_LIMIT,
        include_deleted: bool = False,
    ) -> list[Todo]:
        stmt = select(self.model).where(self.model.completed == completed)
        if not include_deleted:
            stmt = _exclude_deleted(stmt, self.model)
        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_status(self, completed: bool, include_deleted: bool = False) -> int:
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.completed == completed)
        )
        if not include_deleted:
            stmt = _exclude_deleted(stmt, self.model)
        result = await self._session.execute(stmt)
        return result.scalar_one()
