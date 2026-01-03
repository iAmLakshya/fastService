.PHONY: help install dev test lint format typecheck migrate migrate-new seed shell routes clean docker-build docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make dev          - Run development server"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linter"
	@echo "  make format       - Format code"
	@echo "  make typecheck    - Run type checker"
	@echo "  make migrate      - Run database migrations"
	@echo "  make migrate-new  - Create new migration (name=<name>)"
	@echo "  make seed         - Seed database with sample data"
	@echo "  make shell        - Open interactive shell"
	@echo "  make routes       - Show registered routes"
	@echo "  make clean        - Clean build artifacts"
	@echo "  make docker-build - Build Docker images"
	@echo "  make docker-up    - Start Docker containers"
	@echo "  make docker-down  - Stop Docker containers"

install:
	uv sync

dev:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	uv run pytest -v

test-cov:
	uv run pytest -v --cov=app --cov-report=term-missing

lint:
	uv run ruff check . --fix

format:
	uv run ruff format .

typecheck:
	uv run mypy src tests

check: lint format typecheck test

migrate:
	uv run alembic upgrade head

migrate-new:
	uv run alembic revision --autogenerate -m "$(name)"

migrate-down:
	uv run alembic downgrade -1

db-create:
	uv run python -m app.cli db-create

db-drop:
	uv run python -m app.cli db-drop

seed:
	uv run python -m app.cli seed

shell:
	uv run python -m app.cli shell

routes:
	uv run python -m app.cli routes

config:
	uv run python -m app.cli config

new-module:
	uv run python scripts/new_module.py $(name)

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-dev:
	docker compose -f docker-compose.dev.yml up

pre-commit-install:
	uv run pre-commit install

pre-commit-run:
	uv run pre-commit run --all-files
