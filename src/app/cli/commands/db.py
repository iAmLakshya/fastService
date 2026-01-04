import asyncio
from typing import Any

import typer

app = typer.Typer(help="Database management commands")


def run_async(coro: Any) -> Any:
    return asyncio.get_event_loop().run_until_complete(coro)


@app.command()
def create() -> None:
    async def _create() -> None:
        from app.infrastructure import Base, SQLAlchemyAdapter, get_registry
        from app.modules.todos.model import Todo  # noqa: F401

        registry = get_registry()
        db = registry.get_typed("primary", SQLAlchemyAdapter)
        async with db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        typer.echo("Database tables created successfully")

    run_async(_create())


@app.command()
def drop() -> None:
    confirm = typer.confirm("This will drop all tables. Are you sure?")
    if not confirm:
        typer.echo("Aborted")
        raise typer.Exit()

    async def _drop() -> None:
        from app.infrastructure import Base, SQLAlchemyAdapter, get_registry

        registry = get_registry()
        db = registry.get_typed("primary", SQLAlchemyAdapter)
        async with db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        typer.echo("Database tables dropped successfully")

    run_async(_drop())


@app.command()
def reset() -> None:
    confirm = typer.confirm("This will drop and recreate all tables. Are you sure?")
    if not confirm:
        typer.echo("Aborted")
        raise typer.Exit()

    async def _reset() -> None:
        from app.infrastructure import Base, SQLAlchemyAdapter, get_registry
        from app.modules.todos.model import Todo  # noqa: F401

        registry = get_registry()
        db = registry.get_typed("primary", SQLAlchemyAdapter)
        async with db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        typer.echo("Database reset successfully")

    run_async(_reset())


@app.command()
def migrate(
    message: str = typer.Option("auto", "-m", "--message", help="Migration message"),
) -> None:
    import subprocess

    result = subprocess.run(
        ["alembic", "revision", "--autogenerate", "-m", message],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        typer.echo("Migration created successfully")
        typer.echo(result.stdout)
    else:
        typer.echo(f"Error: {result.stderr}", err=True)
        raise typer.Exit(1)


@app.command()
def upgrade(
    revision: str = typer.Argument("head", help="Target revision"),
) -> None:
    import subprocess

    result = subprocess.run(
        ["alembic", "upgrade", revision],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        typer.echo(f"Upgraded to {revision}")
        typer.echo(result.stdout)
    else:
        typer.echo(f"Error: {result.stderr}", err=True)
        raise typer.Exit(1)


@app.command()
def downgrade(
    revision: str = typer.Argument("-1", help="Target revision"),
) -> None:
    import subprocess

    result = subprocess.run(
        ["alembic", "downgrade", revision],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        typer.echo(f"Downgraded to {revision}")
        typer.echo(result.stdout)
    else:
        typer.echo(f"Error: {result.stderr}", err=True)
        raise typer.Exit(1)
