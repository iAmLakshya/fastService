from fastapi import APIRouter, Query, status

from app.infrastructure.constants import Pagination
from app.infrastructure.types import TodoId
from app.modules.todos.dependencies import TodoServiceDep
from app.modules.todos.schemas import TodoCreate, TodoListResponse, TodoResponse, TodoUpdate

router = APIRouter(prefix="/todos", tags=["todos"])


@router.get("", response_model=TodoListResponse)
async def list_todos(
    service: TodoServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(Pagination.DEFAULT_PAGE_SIZE, ge=1, le=Pagination.MAX_PAGE_SIZE),
    completed: bool | None = None,
) -> TodoListResponse:
    result = await service.find_paginated(page=page, page_size=page_size, completed=completed)
    return result.to_response(TodoResponse.model_validate)


@router.get("/{todo_id}", response_model=TodoResponse)
async def get_todo(todo_id: TodoId, service: TodoServiceDep) -> TodoResponse:
    todo = await service.find_by_id(todo_id)
    return TodoResponse.model_validate(todo)


@router.post("", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
async def create_todo(payload: TodoCreate, service: TodoServiceDep) -> TodoResponse:
    todo = await service.create_todo(payload.title, payload.description)
    return TodoResponse.model_validate(todo)


@router.patch("/{todo_id}", response_model=TodoResponse)
async def update_todo(
    todo_id: TodoId,
    payload: TodoUpdate,
    service: TodoServiceDep,
) -> TodoResponse:
    todo = await service.update_todo(
        todo_id,
        payload.title,
        payload.description,
        payload.completed,
    )
    return TodoResponse.model_validate(todo)


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(todo_id: TodoId, service: TodoServiceDep) -> None:
    await service.delete(todo_id)
