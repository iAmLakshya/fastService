# FastAPI Service Boilerplate

Production-ready FastAPI boilerplate with clean, scalable architecture.

## Quick Start

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh  # Install UV
uv sync                                           # Install deps
uv run uvicorn app.main:app --reload              # Run server
uv run pytest                                     # Run tests
```

## Architecture

```
src/app/
├── main.py                  # Application factory
├── config/                  # Configuration management
├── router.py                # Route registry
├── infrastructure/          # Shared infrastructure
│   ├── model.py                 # Base model, mixins
│   ├── repository.py            # Base repository
│   ├── database.py              # Connection management
│   ├── context.py               # Request-scoped session
│   ├── middleware.py            # ASGI middleware
│   ├── lifespan.py              # Startup/shutdown
│   └── exceptions.py            # Error handling
└── modules/                 # Feature modules
    └── todos/
        ├── model.py
        ├── repository.py
        ├── service.py
        ├── router.py
        └── schemas.py
```

## Design Principles

### 1. Request-Scoped Sessions via Context

**Problem:** Traditional FastAPI dependency injection requires threading dependencies through every layer:

```python
# Verbose - session passed everywhere
@router.get("/{id}")
async def get_todo(id: str, session: AsyncSession = Depends(get_session)):
    service = TodoService(session)  # pass to service
    return await service.get_by_id(id)

class TodoService:
    def __init__(self, session: AsyncSession):
        self.repo = TodoRepository(session)  # pass to repo
```

**Solution:** Use [`contextvars`](https://docs.python.org/3/library/contextvars.html) for request-scoped state. Middleware sets the session once, any code can access it:

```python
# Clean - no dependency threading
@router.get("/{id}")
async def get_todo(id: str):
    return await TodoService().get_by_id(id)

class BaseRepository:
    @property
    def _session(self) -> AsyncSession:
        return get_db()  # Gets session from context
```

**Why it scales:**
- Adding new services/repositories doesn't require updating dependency chains
- Function signatures stay clean as the codebase grows
- Services and repositories are plain classes - easy to instantiate and test

### 2. Feature-Based Module Structure

**Problem:** Layer-based structure doesn't scale:

```
# Layer-based - scattered related code
models/
    user.py
    order.py
    product.py      # 50 files...
services/
    user.py
    order.py
    product.py      # 50 more files...
```

**Solution:** Group by feature. Each module is self-contained:

```
modules/
    users/
        model.py
        repository.py
        service.py
        router.py
        schemas.py
    orders/
        ...
```

**Why it scales:**
- Related code stays together - easier navigation
- Clear boundaries - one team can own a module
- Reduced merge conflicts - teams work in different directories
- Easy to delete - remove the folder

### 3. Layered Architecture

```
┌─────────────────────────────────────────┐
│  Router (HTTP layer)                    │  Handles requests, validation
├─────────────────────────────────────────┤
│  Service (Business logic)               │  Orchestrates, enforces rules
├─────────────────────────────────────────┤
│  Repository (Data access)               │  CRUD operations, queries
├─────────────────────────────────────────┤
│  Model (Domain)                         │  SQLAlchemy entities
└─────────────────────────────────────────┘
```

**Single Responsibility:**
- **Router:** HTTP concerns only - request parsing, response formatting
- **Service:** Business logic - validation rules, orchestration, domain operations
- **Repository:** Data access - queries, persistence, no business logic

**Why it scales:**
- Easy to test each layer in isolation
- Business logic is reusable across different routers (REST, GraphQL, CLI)
- Data access patterns are consistent via `BaseRepository`

### 4. Configuration Abstraction

**Problem:** Scattered `os.getenv()` calls are unmaintainable:

```python
# Bad - no validation, no types, no organization
db_url = os.getenv("DATABASE_URL", "sqlite:///app.db")
pool_size = int(os.getenv("POOL_SIZE", "5"))  # crashes if invalid
```

**Solution:** Grouped settings with validation via [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/):

```python
class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DB_")
    url: str = "sqlite+aiosqlite:///./app.db"
    pool_size: int = 5

class AppSettings(BaseSettings):
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)

# Usage
settings.database.url
settings.database.pool_size
```

**Why it scales:**
- Single source of truth for all configuration
- Type-safe, validated at startup
- Grouped by domain - easy to find settings
- Easy to override for testing: `configure(AppSettings(...))`

### 5. ASGI Middleware for Session Lifecycle

**Why ASGI middleware instead of FastAPI dependencies?**

- Guaranteed execution before any route handler
- Full control over the request/response lifecycle
- Automatic commit on success, rollback on error, close on completion
- Works with all routes without explicit decoration

```python
class DBSessionMiddleware:
    async def __call__(self, scope, receive, send):
        async with self.db.session() as session:
            _set_session(session)
            try:
                await self.app(scope, receive, send)
            finally:
                _reset_session()
```

## Adding a Module

```bash
uv run python scripts/new_module.py users
```

Creates:
```
modules/users/
├── model.py
├── repository.py
├── service.py
├── router.py
├── schemas.py
└── __init__.py
```

Register in `router.py`:
```python
from app.modules.users import router as users_router
router.include_router(users_router)
```

## Database

```bash
DB_URL=sqlite+aiosqlite:///./app.db           # SQLite (default)
DB_URL=postgresql+asyncpg://u:p@localhost/db  # PostgreSQL
```

## Docker

```bash
docker compose up --build                    # Production
docker compose -f docker-compose.dev.yml up  # Development
```

## Commands

```bash
uv sync                                   # Install dependencies
uv run uvicorn app.main:app --reload      # Development server
uv run pytest                             # Run tests
uv run python scripts/new_module.py NAME  # Scaffold module
uv run ruff format .                      # Format code
uv run ruff check . --fix                 # Lint code
```

## References

### Architecture
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html) - Uncle Bob's architecture principles
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html) - Martin Fowler's pattern catalog
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID) - Object-oriented design principles

### Python
- [contextvars](https://docs.python.org/3/library/contextvars.html) - Context-local state for async code
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) - Configuration management

### Frameworks
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/) - Database toolkit
- [SQLAlchemy AsyncIO](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) - Async session management

### Tooling
- [UV](https://docs.astral.sh/uv/) - Fast Python package manager
- [Ruff](https://docs.astral.sh/ruff/) - Fast Python linter and formatter
