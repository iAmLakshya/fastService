from typing import Annotated

from fastapi import Depends

from app.modules.todos.service import TodoService


def get_todo_service() -> TodoService:
    return TodoService()


TodoServiceDep = Annotated[TodoService, Depends(get_todo_service)]
