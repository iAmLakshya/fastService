import typer

app = typer.Typer(help="Development commands")


@app.command()
def shell() -> None:
    import code

    from app.config import settings
    from app.infrastructure import Base, get_registry

    banner = f"""
FastAPI Service Shell
=====================
Available objects:
  - settings: Application settings
  - Base: SQLAlchemy declarative base
  - get_registry: Database registry accessor

Environment: {settings.env}
"""
    local_vars = {
        "settings": settings,
        "Base": Base,
        "get_registry": get_registry,
    }
    code.interact(banner=banner, local=local_vars)


@app.command()
def new_module(
    name: str = typer.Argument(..., help="Module name (plural, e.g., 'users')"),
    skip_migration: bool = typer.Option(False, "--skip-migration", help="Skip migration"),
) -> None:
    import subprocess

    args = ["python", "scripts/new_module.py", name]
    if skip_migration:
        args.append("--skip-migration")

    result = subprocess.run(args, capture_output=False)
    raise typer.Exit(result.returncode)


@app.command()
def check() -> None:
    import subprocess

    typer.echo("Running linter...")
    lint_result = subprocess.run(["ruff", "check", "."])

    typer.echo("\nRunning formatter check...")
    format_result = subprocess.run(["ruff", "format", "--check", "."])

    typer.echo("\nRunning type checker...")
    type_result = subprocess.run(["mypy", "src", "tests"])

    if any([lint_result.returncode, format_result.returncode, type_result.returncode]):
        typer.echo("\nSome checks failed!", err=True)
        raise typer.Exit(1)

    typer.echo("\nAll checks passed!")
