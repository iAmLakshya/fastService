#!/usr/bin/env python3
import re
import subprocess
import sys
from pathlib import Path

try:
    from typer import confirm, prompt

    HAS_TYPER = True
except ImportError:
    HAS_TYPER = False
    confirm = None  # type: ignore[assignment]
    prompt = None  # type: ignore[assignment]

SQL_TEMPLATES = {
    "model.py": """from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure import Model


class {class_name}(Model):
    __tablename__ = "{table_name}"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
""",
    "model_soft_delete.py": """from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure import SoftDeletableModel


class {class_name}(SoftDeletableModel):
    __tablename__ = "{table_name}"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
""",
    "repository.py": """from app.infrastructure import BaseSQLRepository
from app.modules.{module_name}.model import {class_name}


class {class_name}Repository(BaseSQLRepository[{class_name}]):
    pass
""",
}

DOCUMENT_TEMPLATES = {
    "document.py": """from typing import Any

from pydantic import Field

from app.infrastructure import SoftDeletableDocument


class {class_name}(SoftDeletableDocument):
    __collection_name__ = "{table_name}"

    name: str
    metadata: dict[str, Any] = Field(default_factory=dict)
""",
    "repository.py": """from app.infrastructure import BaseDocumentRepository
from app.modules.{module_name}.document import {class_name}


class {class_name}Repository(BaseDocumentRepository[{class_name}]):
    pass
""",
}

KV_TEMPLATES = {
    "repository.py": """from typing import Any

from app.infrastructure import BaseKeyValueRepository


class {class_name}Repository(BaseKeyValueRepository[dict[str, Any]]):
    key_prefix = "{module_name}"
""",
}

TEMPLATES = {
    "model.py": SQL_TEMPLATES["model.py"],
    "repository.py": SQL_TEMPLATES["repository.py"],
    "service.py": """from typing import Any

from app.infrastructure import BaseService
from app.modules.{module_name}.model import {class_name}
from app.modules.{module_name}.repository import {class_name}Repository


class {class_name}Service(BaseService[{class_name}, {class_name}Repository]):
    repository_class = {class_name}Repository
    resource_name = "{class_name}"

    async def create(self, name: str, **kwargs: Any) -> {class_name}:
        return await self._repo.create({{"name": name, **kwargs}})

    async def update_name(self, id: str, name: str) -> {class_name}:
        return await self.update(id, {{"name": name}})
""",
    "schemas.py": """from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class {class_name}Create(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class {class_name}Update(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)


class {class_name}Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    created_at: datetime
    updated_at: datetime


class {class_name}ListResponse(BaseModel):
    items: list[{class_name}Response]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
""",
    "router.py": """from fastapi import APIRouter, Query, status

from app.modules.{module_name}.schemas import (
    {class_name}Create,
    {class_name}ListResponse,
    {class_name}Response,
    {class_name}Update,
)
from app.modules.{module_name}.service import {class_name}Service

router = APIRouter(prefix="/{module_name}", tags=["{module_name}"])


@router.get("", response_model={class_name}ListResponse)
async def list_{module_name}(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> {class_name}ListResponse:
    result = await {class_name}Service().find_paginated(page=page, page_size=page_size)
    return {class_name}ListResponse(
        items=[{class_name}Response.model_validate(i) for i in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
        has_next=result.has_next,
        has_prev=result.has_prev,
    )


@router.get("/{{id}}", response_model={class_name}Response)
async def get_{singular}(id: str) -> {class_name}Response:
    item = await {class_name}Service().find_by_id(id)
    return {class_name}Response.model_validate(item)


@router.post("", response_model={class_name}Response, status_code=status.HTTP_201_CREATED)
async def create_{singular}(payload: {class_name}Create) -> {class_name}Response:
    item = await {class_name}Service().create(name=payload.name)
    return {class_name}Response.model_validate(item)


@router.patch("/{{id}}", response_model={class_name}Response)
async def update_{singular}(id: str, payload: {class_name}Update) -> {class_name}Response:
    data = payload.model_dump(exclude_none=True)
    item = await {class_name}Service().update(id, data)
    return {class_name}Response.model_validate(item)


@router.delete("/{{id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_{singular}(id: str) -> None:
    await {class_name}Service().delete(id)
""",
    "__init__.py": """from app.modules.{module_name}.router import router

__all__ = ["router"]
""",
}

TEST_TEMPLATE = """import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_create_{singular}(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/{module_name}",
        json={{"name": "Test {class_name}"}},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test {class_name}"


@pytest.mark.anyio
async def test_list_{module_name}(client: AsyncClient) -> None:
    await client.post("/api/v1/{module_name}", json={{"name": "{class_name} 1"}})
    await client.post("/api/v1/{module_name}", json={{"name": "{class_name} 2"}})

    response = await client.get("/api/v1/{module_name}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2


@pytest.mark.anyio
async def test_get_{singular}(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/{module_name}",
        json={{"name": "Test {class_name}"}},
    )
    created_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/{module_name}/{{created_id}}")
    assert response.status_code == 200
    assert response.json()["id"] == created_id


@pytest.mark.anyio
async def test_get_{singular}_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/v1/{module_name}/nonexistent")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_{singular}(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/{module_name}",
        json={{"name": "Original"}},
    )
    created_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/{module_name}/{{created_id}}",
        json={{"name": "Updated"}},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated"


@pytest.mark.anyio
async def test_delete_{singular}(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/{module_name}",
        json={{"name": "To Delete"}},
    )
    created_id = create_response.json()["id"]

    response = await client.delete(f"/api/v1/{module_name}/{{created_id}}")
    assert response.status_code == 204

    get_response = await client.get(f"/api/v1/{module_name}/{{created_id}}")
    assert get_response.status_code == 404
"""

FACTORY_TEMPLATE = """
class {class_name}Factory(BaseFactory):
    from app.modules.{module_name}.model import {class_name}

    model = {class_name}
    defaults = {{
        "name": "Test {class_name}",
    }}
"""

IRREGULAR_PLURALS = {
    "person": "people",
    "child": "children",
    "man": "men",
    "woman": "women",
    "foot": "feet",
    "tooth": "teeth",
    "goose": "geese",
    "mouse": "mice",
    "sheep": "sheep",
    "deer": "deer",
    "fish": "fish",
    "series": "series",
    "species": "species",
    "analysis": "analyses",
    "basis": "bases",
    "crisis": "crises",
    "diagnosis": "diagnoses",
    "hypothesis": "hypotheses",
    "thesis": "theses",
    "phenomenon": "phenomena",
    "criterion": "criteria",
    "datum": "data",
    "medium": "media",
    "index": "indices",
    "appendix": "appendices",
    "matrix": "matrices",
    "vertex": "vertices",
    "axis": "axes",
    "focus": "foci",
    "nucleus": "nuclei",
    "radius": "radii",
    "stimulus": "stimuli",
    "syllabus": "syllabi",
    "cactus": "cacti",
    "fungus": "fungi",
    "alumnus": "alumni",
    "company": "companies",
    "city": "cities",
    "country": "countries",
    "category": "categories",
    "story": "stories",
    "party": "parties",
    "policy": "policies",
}

IRREGULAR_SINGULARS = {v: k for k, v in IRREGULAR_PLURALS.items()}


def to_singular(name: str) -> str:
    name_lower = name.lower()
    if name_lower in IRREGULAR_SINGULARS:
        return IRREGULAR_SINGULARS[name_lower]
    if name.endswith("ies"):
        return name[:-3] + "y"
    if name.endswith("es") and name[-3] in "sxz":
        return name[:-2]
    if name.endswith("es") and name[-4:-2] in ["ch", "sh"]:
        return name[:-2]
    if name.endswith("s") and not name.endswith("ss"):
        return name[:-1]
    return name


def to_plural(name: str) -> str:
    name_lower = name.lower()
    if name_lower in IRREGULAR_PLURALS:
        return IRREGULAR_PLURALS[name_lower]
    if name.endswith("y") and name[-2] not in "aeiou":
        return name[:-1] + "ies"
    if name.endswith(("s", "x", "z", "ch", "sh")):
        return name + "es"
    return name + "s"


def to_class_name(name: str) -> str:
    singular = to_singular(name)
    words = re.split(r"[_-]", singular)
    return "".join(word.capitalize() for word in words)


def update_router_file(module_name: str) -> None:
    router_path = Path("src/app/router.py")
    if not router_path.exists():
        return

    content = router_path.read_text()

    import_line = f"from app.modules.{module_name} import router as {module_name}_router"
    include_line = f"router.include_router({module_name}_router)"

    if import_line in content:
        return

    lines = content.split("\n")
    import_section_end = 0
    for i, line in enumerate(lines):
        is_import = line.startswith(("from app.modules", "from ", "import "))
        if is_import:
            import_section_end = i + 1

    lines.insert(import_section_end, import_line)

    for i, line in enumerate(lines):
        if "router.include_router" in line:
            lines.insert(i + 1, include_line)
            break
    else:
        lines.append(include_line)

    router_path.write_text("\n".join(lines))
    print(f"  Updated: {router_path}")


def update_alembic_env(module_name: str, class_name: str) -> None:
    env_path = Path("alembic/env.py")
    if not env_path.exists():
        return

    content = env_path.read_text()
    import_line = f"from app.modules.{module_name}.model import {class_name}  # noqa: F401"

    if import_line in content:
        return

    lines = content.split("\n")
    for i, line in enumerate(lines):
        if "from app.modules" in line and "model import" in line:
            lines.insert(i + 1, import_line)
            break

    env_path.write_text("\n".join(lines))
    print(f"  Updated: {env_path}")


def update_factories(module_name: str, class_name: str, singular: str) -> None:
    factories_path = Path("tests/factories.py")
    if not factories_path.exists():
        return

    content = factories_path.read_text()
    factory_class = f"class {class_name}Factory"

    if factory_class in content:
        return

    factory_code = FACTORY_TEMPLATE.format(
        module_name=module_name,
        class_name=class_name,
        singular=singular,
    )

    content = content.rstrip() + "\n" + factory_code
    factories_path.write_text(content)
    print(f"  Updated: {factories_path}")


class GenerationOptions:
    def __init__(
        self,
        db_type: str = "sql",
        generate_model: bool = True,
        generate_repo: bool = True,
        generate_service: bool = True,
        generate_router: bool = True,
        generate_schemas: bool = True,
        generate_tests: bool = True,
        generate_factory: bool = True,
        run_migration: bool = True,
        use_soft_delete: bool = True,
    ):
        self.db_type = db_type
        self.generate_model = generate_model
        self.generate_repo = generate_repo
        self.generate_service = generate_service
        self.generate_router = generate_router
        self.generate_schemas = generate_schemas
        self.generate_tests = generate_tests
        self.generate_factory = generate_factory
        self.run_migration = run_migration
        self.use_soft_delete = use_soft_delete


def interactive_prompts(module_name: str) -> GenerationOptions:
    if not HAS_TYPER:
        print("Typer not installed, using defaults")
        return GenerationOptions()

    print(f"\n{'='*50}")
    print(f"  Generating module: {module_name}")
    print(f"{'='*50}\n")

    db_type = prompt(
        "Database type [sql/document/kv]",
        default="sql",
        show_default=True,
    )
    if db_type not in ("sql", "document", "kv"):
        print(f"Invalid db_type '{db_type}', using 'sql'")
        db_type = "sql"

    use_soft_delete = False
    if db_type in ("sql", "document"):
        use_soft_delete = confirm("  Enable soft delete?", default=True)

    print("\nSelect files to generate:\n")

    if db_type == "sql":
        gen_model = confirm("  model.py (SQLAlchemy model)?", default=True)
    elif db_type == "document":
        gen_model = confirm("  document.py (Pydantic document)?", default=True)
    else:
        gen_model = False

    gen_repo = confirm("  repository.py?", default=True)
    gen_service = confirm("  service.py?", default=True) if db_type == "sql" else False
    gen_router = confirm("  router.py?", default=True) if db_type == "sql" else False
    gen_schemas = confirm("  schemas.py?", default=True) if db_type == "sql" else False
    gen_tests = confirm("  tests?", default=True) if db_type == "sql" else False
    gen_factory = confirm("  Add to factories.py?", default=True) if db_type == "sql" else False
    run_mig = confirm("  Create alembic migration?", default=True) if db_type == "sql" else False

    return GenerationOptions(
        db_type=db_type,
        generate_model=gen_model,
        generate_repo=gen_repo,
        generate_service=gen_service,
        generate_router=gen_router,
        generate_schemas=gen_schemas,
        generate_tests=gen_tests,
        generate_factory=gen_factory,
        run_migration=run_mig,
        use_soft_delete=use_soft_delete,
    )


def create_module(
    module_name: str,
    options: GenerationOptions | None = None,
) -> None:
    module_dir = Path(f"src/app/modules/{module_name}")

    if module_dir.exists():
        print(f"Error: Module '{module_name}' already exists")
        sys.exit(1)

    if options is None:
        options = GenerationOptions()

    module_dir.mkdir(parents=True)

    class_name = to_class_name(module_name)
    singular = to_singular(module_name)
    table_name = module_name

    soft_delete_str = "with soft-delete" if options.use_soft_delete else "without soft-delete"
    print(f"\nCreating module '{module_name}' ({options.db_type}, {soft_delete_str})...")
    print(f"  Class: {class_name}")
    print(f"  Singular: {singular}")
    print(f"  Table/Collection: {table_name}")
    print()

    if options.db_type == "sql":
        templates = {**TEMPLATES}
        if options.use_soft_delete:
            templates["model.py"] = SQL_TEMPLATES["model_soft_delete.py"]
        else:
            templates["model.py"] = SQL_TEMPLATES["model.py"]
    elif options.db_type == "document":
        templates = {**DOCUMENT_TEMPLATES}
        if not options.use_soft_delete:
            templates["document.py"] = templates["document.py"].replace(
                "SoftDeletableDocument", "BaseDocument"
            ).replace(
                "from app.infrastructure import SoftDeletableDocument",
                "from app.infrastructure import BaseDocument"
            )
    else:
        templates = {**KV_TEMPLATES}

    files_to_generate = []
    if options.generate_model:
        if options.db_type == "sql" and "model.py" in templates:
            files_to_generate.append("model.py")
        elif options.db_type == "document" and "document.py" in templates:
            files_to_generate.append("document.py")
    if options.generate_repo and "repository.py" in templates:
        files_to_generate.append("repository.py")
    if options.generate_service and "service.py" in TEMPLATES:
        files_to_generate.append("service.py")
        templates["service.py"] = TEMPLATES["service.py"]
    if options.generate_router and "router.py" in TEMPLATES:
        files_to_generate.append("router.py")
        templates["router.py"] = TEMPLATES["router.py"]
    if options.generate_schemas and "schemas.py" in TEMPLATES:
        files_to_generate.append("schemas.py")
        templates["schemas.py"] = TEMPLATES["schemas.py"]
    files_to_generate.append("__init__.py")
    templates["__init__.py"] = TEMPLATES["__init__.py"]

    for filename in files_to_generate:
        if filename in templates:
            content = templates[filename].format(
                module_name=module_name,
                class_name=class_name,
                table_name=table_name,
                singular=singular,
            )
            (module_dir / filename).write_text(content)
            print(f"  Created: {module_dir / filename}")

    if options.generate_tests and options.db_type == "sql":
        test_file = Path(f"tests/test_{module_name}.py")
        test_content = TEST_TEMPLATE.format(
            module_name=module_name,
            class_name=class_name,
            singular=singular,
        )
        test_file.write_text(test_content)
        print(f"  Created: {test_file}")

    if options.generate_router and options.db_type == "sql":
        update_router_file(module_name)

    if options.db_type == "sql":
        update_alembic_env(module_name, class_name)

    if options.generate_factory and options.db_type == "sql":
        update_factories(module_name, class_name, singular)

    if options.run_migration and options.db_type == "sql":
        print("\n  Generating migration...")
        try:
            result = subprocess.run(
                ["uv", "run", "alembic", "revision", "--autogenerate", "-m", f"add_{module_name}"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print("  Migration generated successfully")
            else:
                print(f"  Warning: Could not generate migration: {result.stderr}")
        except FileNotFoundError:
            print("  Warning: Could not generate migration (alembic not found)")

    print(f"\n Module '{module_name}' created successfully")

    if options.db_type == "sql":
        print("\nNext steps:")
        print(f"  1. Edit src/app/modules/{module_name}/model.py to customize fields")
        print("  2. Update the generated migration if needed")
        print("  3. Run: uv run alembic upgrade head")
        if options.generate_tests:
            print(f"  4. Run tests: uv run pytest tests/test_{module_name}.py")
    elif options.db_type == "document":
        print("\nNext steps:")
        print(f"  1. Edit src/app/modules/{module_name}/document.py to customize fields")
        print("  2. Ensure MongoDB is configured and enabled")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/new_module.py <module_name> [options]")
        print()
        print("Options:")
        print("  --quick            Use all defaults, no prompts")
        print("  --db-type=TYPE     Database type: sql, document, kv (default: sql)")
        print("  --soft-delete      Enable soft delete (default)")
        print("  --no-soft-delete   Disable soft delete")
        print("  --skip-migration   Skip alembic migration generation")
        print("  --skip-tests       Skip test file generation")
        print()
        print("Examples:")
        print("  uv run python scripts/new_module.py users")
        print("  uv run python scripts/new_module.py users --quick")
        print("  uv run python scripts/new_module.py users --quick --no-soft-delete")
        print("  uv run python scripts/new_module.py profiles --db-type=document")
        print("  uv run python scripts/new_module.py cache --db-type=kv")
        sys.exit(1)

    module_name = sys.argv[1]
    quick = "--quick" in sys.argv
    skip_migration = "--skip-migration" in sys.argv
    skip_tests = "--skip-tests" in sys.argv
    no_soft_delete = "--no-soft-delete" in sys.argv
    use_soft_delete = "--soft-delete" in sys.argv or not no_soft_delete

    db_type = "sql"
    for arg in sys.argv:
        if arg.startswith("--db-type="):
            db_type = arg.split("=")[1]

    if quick:
        options = GenerationOptions(
            db_type=db_type,
            run_migration=not skip_migration,
            generate_tests=not skip_tests,
            use_soft_delete=use_soft_delete,
        )
    else:
        if HAS_TYPER and sys.stdin.isatty():
            options = interactive_prompts(module_name)
        else:
            options = GenerationOptions(
                db_type=db_type,
                run_migration=not skip_migration,
                generate_tests=not skip_tests,
                use_soft_delete=use_soft_delete,
            )

    create_module(module_name, options)
