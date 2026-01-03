from fastapi import APIRouter, Query, status

from app.modules.todos.schemas import TodoCreate, TodoListResponse, TodoResponse, TodoUpdate
from app.modules.todos.service import TodoService

router = APIRouter(prefix="/todos", tags=["todos"])


@router.get("", response_model=TodoListResponse)
async def list_todos(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    completed: bool | None = None,
) -> TodoListResponse:
    todos = await TodoService().get_all(skip=skip, limit=limit, completed=completed)
    return TodoListResponse(
        items=[TodoResponse.model_validate(t) for t in todos],
        total=len(todos),
    )


@router.get("/{todo_id}", response_model=TodoResponse)
async def get_todo(todo_id: str) -> TodoResponse:
    todo = await TodoService().get_by_id(todo_id)
    return TodoResponse.model_validate(todo)


@router.post("", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
async def create_todo(payload: TodoCreate) -> TodoResponse:
    todo = await TodoService().create(title=payload.title, description=payload.description)
    return TodoResponse.model_validate(todo)


@router.patch("/{todo_id}", response_model=TodoResponse)
async def update_todo(todo_id: str, payload: TodoUpdate) -> TodoResponse:
    todo = await TodoService().update(
        todo_id=todo_id,
        title=payload.title,
        description=payload.description,
        completed=payload.completed,
    )
    return TodoResponse.model_validate(todo)


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(todo_id: str) -> None:
    await TodoService().delete(todo_id)
