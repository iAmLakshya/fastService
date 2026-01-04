import typer

app = typer.Typer(help="Server management commands")


@app.command()
def run(
    host: str = typer.Option("0.0.0.0", help="Host to bind"),
    port: int = typer.Option(8000, help="Port to bind"),
    reload: bool = typer.Option(False, help="Enable auto-reload"),
    workers: int = typer.Option(1, help="Number of workers"),
) -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers if not reload else 1,
    )


@app.command()
def routes() -> None:
    from starlette.routing import Route

    from app.main import create_app

    fastapi_app = create_app()

    typer.echo("\nRegistered Routes:")
    typer.echo("-" * 60)

    for route in fastapi_app.routes:
        if isinstance(route, Route) and route.methods:
            methods = ", ".join(route.methods)
            typer.echo(f"{methods:20} {route.path}")


@app.command()
def config() -> None:
    from app.config import settings

    typer.echo("\nCurrent Configuration:")
    typer.echo("-" * 40)
    typer.echo(f"App Name:     {settings.name}")
    typer.echo(f"Version:      {settings.version}")
    typer.echo(f"Environment:  {settings.env}")
    typer.echo(f"Debug:        {settings.debug}")
    if settings.databases.sql.enabled:
        typer.echo(f"Database:     {settings.databases.sql.url}")
    if settings.databases.redis.enabled:
        typer.echo(f"Redis:        {settings.databases.redis.url}")
    typer.echo(f"Rate Limit:   {settings.ratelimit.enabled}")
    typer.echo(f"CORS:         {settings.cors.enabled}")
    typer.echo(f"Log Level:    {settings.logging.level}")
