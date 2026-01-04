import typer

from app.cli.commands import db, dev, seed, server

app = typer.Typer(
    name="app",
    help="FastAPI Service CLI",
    no_args_is_help=True,
)

app.add_typer(server.app, name="server")
app.add_typer(db.app, name="db")
app.add_typer(seed.app, name="seed")
app.add_typer(dev.app, name="dev")


@app.command()
def version() -> None:
    from app.config import settings

    typer.echo(f"{settings.name} v{settings.version}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
