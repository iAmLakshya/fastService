from app.infrastructure import NotFoundError
from app.modules.todos.model import Todo
from app.modules.todos.repository import TodoRepository


class TodoService:
    def __init__(self) -> None:
        self._repo = TodoRepository()

    async def get_all(
        self, skip: int = 0, limit: int = 100, completed: bool | None = None
    ) -> list[Todo]:
        if completed is not None:
            return await self._repo.get_by_completed_status(completed, skip, limit)
        return await self._repo.get_all(skip, limit)

    async def get_by_id(self, todo_id: str) -> Todo:
        todo = await self._repo.get_by_id(todo_id)
        if not todo:
            raise NotFoundError("Todo", todo_id)
        return todo

    async def create(self, title: str, description: str | None = None) -> Todo:
        return await self._repo.create({
            "title": title,
            "description": description,
        })

    async def update(
        self,
        todo_id: str,
        title: str | None = None,
        description: str | None = None,
        completed: bool | None = None,
    ) -> Todo:
        data = {}
        if title is not None:
            data["title"] = title
        if description is not None:
            data["description"] = description
        if completed is not None:
            data["completed"] = completed

        if not data:
            return await self.get_by_id(todo_id)

        todo = await self._repo.update(todo_id, data)
        if not todo:
            raise NotFoundError("Todo", todo_id)
        return todo

    async def delete(self, todo_id: str) -> None:
        deleted = await self._repo.delete(todo_id)
        if not deleted:
            raise NotFoundError("Todo", todo_id)
