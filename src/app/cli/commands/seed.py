import typer

from app.cli.utils import db_session, run_async
from app.infrastructure.constants import Seeder

app = typer.Typer(help="Database seeding commands")


def _import_seeders() -> None:
    from app.modules.todos import seeder  # noqa: F401


def _print_results(results: dict[str, int], action: str) -> None:
    for seeder_name, item_count in results.items():
        typer.echo(f"  {seeder_name}: {item_count} items {action}")
    typer.echo(f"\nTotal: {sum(results.values())} items {action}")


def _handle_seeder_error(error: ValueError) -> None:
    from app.seeders import get_seeder_names

    typer.echo(f"Error: {error}", err=True)
    typer.echo(f"Available seeders: {', '.join(get_seeder_names())}")
    raise typer.Exit(1) from None


@app.command("run")
def run_seeders(
    name: str = typer.Argument(None, help="Seeder name (or 'all' for all seeders)"),
    count: int = typer.Option(
        Seeder.DEFAULT_COUNT, "-c", "--count", help="Number of items to create"
    ),
) -> None:
    _import_seeders()

    async def execute() -> None:
        from app.seeders import run_all_seeders, run_seeder

        async with db_session():
            try:
                if name is None or name == "all":
                    results = await run_all_seeders(count=count)
                    _print_results(results, "created")
                else:
                    seeded_count = await run_seeder(name, count=count)
                    typer.echo(f"  {name}: {seeded_count} items created")
            except ValueError as e:
                _handle_seeder_error(e)

    run_async(execute())


@app.command("clear")
def clear_seeders(
    name: str = typer.Argument(None, help="Seeder name (or 'all' for all seeders)"),
) -> None:
    _import_seeders()

    async def execute() -> None:
        from app.seeders import clear_all_seeders, clear_seeder

        async with db_session():
            try:
                if name is None or name == "all":
                    results = await clear_all_seeders()
                    _print_results(results, "cleared")
                else:
                    cleared_count = await clear_seeder(name)
                    typer.echo(f"  {name}: {cleared_count} items cleared")
            except ValueError as e:
                _handle_seeder_error(e)

    run_async(execute())


@app.command("list")
def list_seeders() -> None:
    _import_seeders()

    from app.seeders import get_all_seeders

    typer.echo("\nAvailable Seeders:")
    typer.echo("-" * 40)
    for seeder_class in get_all_seeders():
        typer.echo(f"  {seeder_class.name} (order: {seeder_class.order})")
