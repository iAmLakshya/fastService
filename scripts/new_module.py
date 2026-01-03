#!/usr/bin/env python3
"""Scaffold a new module.

Usage:
    uv run python scripts/new_module.py users
    uv run python scripts/new_module.py products
"""

import sys
from pathlib import Path

TEMPLATES = {
    "model.py": '''from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure import Base, TimestampMixin, UUIDMixin


class {class_name}(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "{table_name}"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
''',
    "repository.py": '''from app.infrastructure import BaseRepository
from app.modules.{module_name}.model import {class_name}


class {class_name}Repository(BaseRepository[{class_name}]):
    model = {class_name}
''',
    "service.py": '''from app.infrastructure import NotFoundError
from app.modules.{module_name}.model import {class_name}
from app.modules.{module_name}.repository import {class_name}Repository


class {class_name}Service:
    def __init__(self) -> None:
        self._repo = {class_name}Repository()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[{class_name}]:
        return await self._repo.get_all(skip, limit)

    async def get_by_id(self, id: str) -> {class_name}:
        item = await self._repo.get_by_id(id)
        if not item:
            raise NotFoundError("{class_name}", id)
        return item

    async def create(self, name: str) -> {class_name}:
        return await self._repo.create({{"name": name}})

    async def delete(self, id: str) -> None:
        deleted = await self._repo.delete(id)
        if not deleted:
            raise NotFoundError("{class_name}", id)
''',
    "schemas.py": '''from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class {class_name}Create(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class {class_name}Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    created_at: datetime
    updated_at: datetime


class {class_name}ListResponse(BaseModel):
    items: list[{class_name}Response]
    total: int
''',
    "router.py": '''from fastapi import APIRouter, Query, status

from app.modules.{module_name}.schemas import (
    {class_name}Create,
    {class_name}ListResponse,
    {class_name}Response,
)
from app.modules.{module_name}.service import {class_name}Service

router = APIRouter(prefix="/{module_name}", tags=["{module_name}"])


@router.get("", response_model={class_name}ListResponse)
async def list_{module_name}(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> {class_name}ListResponse:
    items = await {class_name}Service().get_all(skip=skip, limit=limit)
    return {class_name}ListResponse(
        items=[{class_name}Response.model_validate(i) for i in items],
        total=len(items),
    )


@router.get("/{{id}}", response_model={class_name}Response)
async def get_{singular}(id: str) -> {class_name}Response:
    item = await {class_name}Service().get_by_id(id)
    return {class_name}Response.model_validate(item)


@router.post("", response_model={class_name}Response, status_code=status.HTTP_201_CREATED)
async def create_{singular}(payload: {class_name}Create) -> {class_name}Response:
    item = await {class_name}Service().create(name=payload.name)
    return {class_name}Response.model_validate(item)


@router.delete("/{{id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_{singular}(id: str) -> None:
    await {class_name}Service().delete(id)
''',
    "__init__.py": '''from app.modules.{module_name}.router import router

__all__ = ["router"]
''',
}


def to_class_name(name: str) -> str:
    """users -> User, products -> Product"""
    singular = name.rstrip("s") if name.endswith("s") else name
    return singular.title()


def to_singular(name: str) -> str:
    """users -> user, products -> product"""
    return name.rstrip("s") if name.endswith("s") else name


def create_module(module_name: str) -> None:
    module_dir = Path(f"src/app/modules/{module_name}")

    if module_dir.exists():
        print(f"Error: Module '{module_name}' already exists")
        sys.exit(1)

    module_dir.mkdir(parents=True)

    class_name = to_class_name(module_name)
    singular = to_singular(module_name)

    for filename, template in TEMPLATES.items():
        content = template.format(
            module_name=module_name,
            class_name=class_name,
            table_name=module_name,
            singular=singular,
        )
        (module_dir / filename).write_text(content)
        print(f"  Created: {module_dir / filename}")

    print(f"\n✓ Module '{module_name}' created")
    print("\nNext steps:")
    print(f"  1. Edit src/app/modules/{module_name}/model.py to add fields")
    print("  2. Register router in src/app/router.py:")
    print(f"     from app.modules.{module_name} import router as {module_name}_router")
    print(f"     router.include_router({module_name}_router)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run python scripts/new_module.py <module_name>")
        print("Example: uv run python scripts/new_module.py users")
        sys.exit(1)

    create_module(sys.argv[1])
