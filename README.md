# FastService

Production-ready FastAPI boilerplate with clean, scalable architecture.

[![CI](https://github.com/iAmLakshya/fastService/actions/workflows/ci.yml/badge.svg)](https://github.com/iAmLakshya/fastService/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Quick Start

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh  # Install UV
uv sync                                           # Install deps
uv run uvicorn app.main:app --reload              # Run server
```

Visit `http://localhost:8000/docs` for API documentation.

## Features

- **Clean Architecture** - Layered design with clear separation of concerns
- **Async First** - Full async/await support with SQLAlchemy 2.0
- **Type Safe** - 100% type hints with strict mypy checking
- **Database Migrations** - Alembic integration for schema versioning
- **Structured Logging** - JSON logging with request correlation IDs
- **Pagination** - Built-in offset and cursor-based pagination
- **Caching** - Redis caching with decorator-based invalidation
- **Background Tasks** - Async task queue with arq
- **Rate Limiting** - Configurable rate limits per endpoint
- **WebSocket Support** - Connection manager for real-time features
- **Event System** - Publish/subscribe for decoupled components
- **Health Checks** - Kubernetes-ready health endpoints
- **CLI Tools** - Modular management commands
- **Test Factories** - Factory pattern for test data generation
- **Module Scaffolding** - Auto-generate new feature modules
- **Scalable Seeding** - Module-based database seeders

## Architecture

```
src/app/
├── main.py                      # Application factory
├── router.py                    # Route registry
├── config/                      # Configuration management
│   ├── base.py                      # Settings classes
│   ├── database.py                  # Database settings
│   └── __init__.py                  # Settings access
├── cli/                         # CLI commands
│   ├── __init__.py                  # Main CLI app
│   └── commands/                    # Command modules
│       ├── server.py                # Server commands
│       ├── db.py                    # Database commands
│       ├── seed.py                  # Seeding commands
│       └── dev.py                   # Development commands
├── seeders/                     # Database seeders
│   └── __init__.py                  # Seeder base class
├── infrastructure/              # Shared infrastructure
│   ├── core/                        # Core infrastructure
│   │   ├── context.py               # Request context
│   │   ├── lifespan.py              # App lifecycle
│   │   ├── setup.py                 # App setup
│   │   ├── health.py                # Health endpoints
│   │   └── middleware/              # Middleware stack
│   │       ├── request_id.py        # Request ID
│   │       ├── db_session.py        # DB session
│   │       └── logging.py           # Request logging
│   ├── persistence/                 # Data layer
│   │   ├── model.py                 # Base models, mixins
│   │   ├── service.py               # Base service
│   │   ├── adapters/                # Database adapters
│   │   │   ├── sqlalchemy.py        # SQL adapter
│   │   │   ├── mongo.py             # MongoDB adapter
│   │   │   ├── redis.py             # Redis adapter
│   │   │   └── registry.py          # Adapter registry
│   │   └── repository/              # Repository layer
│   │       ├── sql/                 # SQL repositories
│   │       ├── document/            # Document repositories
│   │       └── kv/                  # Key-value repositories
│   ├── web/                         # Web layer
│   │   ├── exceptions/              # Error handling (RFC 7807)
│   │   ├── pagination/              # Pagination utilities
│   │   ├── ratelimit.py             # Rate limiting
│   │   └── websocket.py             # WebSocket manager
│   ├── messaging/                   # Async messaging
│   │   ├── events.py                # Event system
│   │   ├── tasks.py                 # Background tasks
│   │   └── cache.py                 # Caching
│   ├── observability/               # Logging, tracing
│   │   └── logging.py               # Structured logging
│   └── types.py                     # Type-safe IDs
└── modules/                     # Feature modules
    └── todos/
        ├── model.py
        ├── repository.py
        ├── service.py
        ├── router.py
        ├── schemas.py
        └── seeder.py
```

## Design Principles

### 1. Request-Scoped Sessions via Context

Use `contextvars` for request-scoped state. Middleware sets the session once, any code can access it:

```python
@router.get("/{id}")
async def get_todo(id: str):
    return await TodoService().get_by_id(id)

class BaseRepository:
    @property
    def _session(self) -> AsyncSession:
        return get_db()  # Gets session from context
```

### 2. Feature-Based Module Structure

Group by feature. Each module is self-contained:

```
modules/
    users/
        model.py
        repository.py
        service.py
        router.py
        schemas.py
        seeder.py
```

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

### 4. Generic Base Classes

```python
class TodoRepository(BaseRepository[Todo]):
    model = Todo

class TodoService(BaseService[Todo, TodoRepository]):
    repository_class = TodoRepository
    resource_name = "Todo"
```

Built-in methods: `get_by_id`, `get_all`, `get_paginated`, `create`, `update`, `delete`, `bulk_create`, `bulk_update`, `bulk_delete`, `get_or_create`, `upsert`, `exists`, `count`, `restore`

## Adding a Module

```bash
make new-module name=users
# or
uv run python scripts/new_module.py users
```

This creates:
- Model with soft delete support
- Repository extending BaseRepository
- Service extending BaseService
- Router with CRUD endpoints
- Pydantic schemas with pagination
- Test file with basic tests
- Alembic migration
- Factory for testing
- Seeder for sample data

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
APP_NAME=FastAPI Service
APP_ENV=development  # development, staging, production
DEBUG=true
SECRET_KEY=change-me-in-production

DB_SQL_ENABLED=true
DB_SQL_URL=sqlite+aiosqlite:///./app.db
DB_SQL_ECHO=false
DB_SQL_POOL_SIZE=5

DB_REDIS_ENABLED=false
DB_REDIS_URL=redis://localhost:6379/0

DB_MONGO_ENABLED=false
DB_MONGO_URL=mongodb://localhost:27017
DB_MONGO_DATABASE=app

RATELIMIT_ENABLED=false
RATELIMIT_DEFAULT=100/minute

CORS_ENABLED=true
CORS_ORIGINS=["http://localhost:3000"]

LOG_LEVEL=INFO
LOG_JSON_FORMAT=false
```

## CLI Commands

The CLI is organized into command groups:

```bash
# Server commands
uv run python -m app.cli server run          # Start server
uv run python -m app.cli server routes       # List routes
uv run python -m app.cli server config       # Show config

# Database commands
uv run python -m app.cli db create           # Create tables
uv run python -m app.cli db drop             # Drop tables
uv run python -m app.cli db reset            # Drop and recreate
uv run python -m app.cli db migrate -m "msg" # Create migration
uv run python -m app.cli db upgrade          # Run migrations
uv run python -m app.cli db downgrade        # Rollback migration

# Seeding commands
uv run python -m app.cli seed run            # Run all seeders
uv run python -m app.cli seed run todos      # Run specific seeder
uv run python -m app.cli seed run -c 20      # Create 20 items
uv run python -m app.cli seed clear          # Clear all seeded data
uv run python -m app.cli seed list           # List available seeders

# Development commands
uv run python -m app.cli dev shell           # Interactive shell
uv run python -m app.cli dev new-module users # Scaffold module
uv run python -m app.cli dev check           # Run all checks
```

## Database Seeders

Seeders provide scalable, module-based data generation:

```python
# modules/users/seeder.py
from app.seeders import Seeder, register_seeder

@register_seeder
class UserSeeder(Seeder):
    name = "users"
    order = 10  # Lower runs first

    async def run(self, count: int = 10) -> int:
        # Create sample data
        return created_count

    async def clear(self) -> int:
        # Remove seeded data
        return deleted_count
```

## Testing

```bash
make test           # Run tests
make test-cov       # With coverage
```

Using factories:

```python
@pytest.mark.anyio
async def test_with_factory(todo_factory):
    todo = await todo_factory.create(title="Test")
    assert todo.title == "Test"
```

## Development

```bash
make dev            # Run dev server
make lint           # Run linter
make format         # Format code
make typecheck      # Type check
make check          # All checks
```

## Docker

```bash
make docker-build   # Build image
make docker-up      # Start containers
make docker-down    # Stop containers
make docker-dev     # Development mode
```

## Infrastructure Features

### Pagination

```python
result = await service.get_paginated(page=1, page_size=20)
# Returns: PageResult with items, total, page, page_size, total_pages, has_next, has_prev
```

### Caching

```python
from app.infrastructure import cached

@cached(ttl=300)
async def get_expensive_data():
    ...
```

### Background Tasks

```python
from app.infrastructure import enqueue

await enqueue("send_email", user_id=123)
```

### Events

```python
from app.infrastructure import emit, on

@on("user.created")
async def send_welcome_email(user):
    ...

await emit("user.created", user)
```

### Soft Delete

Models with `SoftDeleteMixin` support soft delete:

```python
await service.delete(id)             # Soft delete
await service.delete(id, hard=True)  # Hard delete
await service.restore(id)            # Restore
```

### Rate Limiting

```python
from app.infrastructure import limiter

@router.get("/")
@limiter.limit("10/minute")
async def limited_endpoint(request: Request):
    ...
```

### WebSocket

```python
from app.infrastructure import manager

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(client_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(data)
    except WebSocketDisconnect:
        await manager.disconnect(client_id)
```

## Error Handling

Errors follow RFC 7807 Problem Details:

```json
{
    "type": "/errors/not-found",
    "title": "Not Found",
    "status": 404,
    "detail": "Todo with id 'xyz' not found",
    "instance": "/api/v1/todos/xyz"
}
```

## Health Checks

```bash
GET /health        # Full health check (DB connectivity)
GET /health/ready  # Readiness probe
GET /health/live   # Liveness probe
```

## Project Structure

```bash
.
├── src/app/           # Application code
├── tests/             # Test suite
├── alembic/           # Database migrations
├── scripts/           # Utility scripts
├── Makefile           # Development commands
├── pyproject.toml     # Dependencies
├── Dockerfile         # Production image
└── docker-compose.yml # Container orchestration
```

## References

### Architecture
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)

### Documentation
- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)
- [Pydantic](https://docs.pydantic.dev/)
- [Alembic](https://alembic.sqlalchemy.org/)

### Tooling
- [UV](https://docs.astral.sh/uv/)
- [Ruff](https://docs.astral.sh/ruff/)

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) before submitting a PR.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
