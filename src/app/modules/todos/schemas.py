from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.infrastructure.types import TodoId
from app.infrastructure.web.pagination import PaginatedResponse


class TodoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)


class TodoUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    completed: bool | None = None


class TodoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: TodoId
    title: str
    description: str | None
    completed: bool
    created_at: datetime
    updated_at: datetime


TodoListResponse = PaginatedResponse[TodoResponse]
