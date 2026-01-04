from app.infrastructure.constants import Seeder as SeederDefaults
from app.modules.todos.service import TodoService
from app.seeders import Seeder, register_seeder

SAMPLE_TODOS = [
    {"title": "Learn FastAPI", "description": "Read the official documentation"},
    {"title": "Set up the project", "description": "Initialize repository and deps"},
    {"title": "Design the database schema", "description": "Create ERD and models"},
    {"title": "Implement authentication", "description": "Add JWT-based auth"},
    {"title": "Write API endpoints", "description": "Create CRUD operations"},
    {"title": "Add validation", "description": "Implement Pydantic validation"},
    {"title": "Write unit tests", "description": "Cover business logic with tests"},
    {"title": "Write integration tests", "description": "Test API endpoints"},
    {"title": "Set up CI/CD", "description": "Configure GitHub Actions"},
    {"title": "Deploy to production", "description": "Deploy to cloud provider"},
]


@register_seeder
class TodoSeeder(Seeder):
    name = "todos"
    order = 10

    def __init__(self) -> None:
        self.service = TodoService()

    async def run(self, count: int = SeederDefaults.DEFAULT_COUNT) -> int:
        created = 0
        for data in SAMPLE_TODOS[:count]:
            await self.service.create_todo(data["title"], data["description"])
            created += 1
        return created

    async def clear(self) -> int:
        todos = await self.service.find_all(limit=SeederDefaults.CLEAR_FETCH_LIMIT)
        for todo in todos:
            await self.service.delete(todo.id, hard=True)
        return len(todos)
