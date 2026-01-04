from app.infrastructure import BaseService, PageResult, paginate
from app.infrastructure.constants import Pagination
from app.modules.todos.model import Todo
from app.modules.todos.repository import TodoRepository


class TodoService(BaseService[Todo, TodoRepository]):
    async def find_all(
        self,
        offset: int = 0,
        limit: int = Pagination.DEFAULT_LIMIT,
        include_deleted: bool = False,
        *,
        completed: bool | None = None,
    ) -> list[Todo]:
        if completed is not None:
            return await self._repo.find_by_status(completed, offset, limit)
        return await self._repo.find_all(offset, limit, include_deleted)

    async def find_paginated(
        self,
        page: int = 1,
        page_size: int = Pagination.DEFAULT_PAGE_SIZE,
        include_deleted: bool = False,
        *,
        completed: bool | None = None,
    ) -> PageResult[Todo]:
        if completed is not None:
            offset = (page - 1) * page_size
            items = await self._repo.find_by_status(completed, offset, page_size)
            total = await self._repo.count_by_status(completed)
        else:
            items, total = await self._repo.find_paginated(page, page_size, include_deleted)

        return paginate(items, total, page, page_size)

    async def create_todo(self, title: str, description: str | None = None) -> Todo:
        return await self._repo.create({"title": title, "description": description})

    async def update_todo(
        self,
        todo_id: str,
        title: str | None = None,
        description: str | None = None,
        completed: bool | None = None,
    ) -> Todo:
        data: dict[str, object] = {}
        if title is not None:
            data["title"] = title
        if description is not None:
            data["description"] = description
        if completed is not None:
            data["completed"] = completed

        return await self.update(todo_id, data)
