import asyncio
import urllib.parse
import webbrowser

import typer
import uvicorn

from spotify_mcp.config import settings
from spotify_mcp.db.session import init_db
from spotify_mcp.main import app as login_app
from spotify_mcp.mcp.server import mcp_server
from spotify_mcp.spotify import auth as auth_module

cli = typer.Typer(
    name="spotify-mcp",
    help="MCP server for the Spotify Web API.",
    add_completion=False,
)


@cli.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Run the MCP server over stdio. This is what your MCP host should launch."""
    if ctx.invoked_subcommand is not None:
        return
    init_db()
    mcp_server.run()  # defaults to transport="stdio"


@cli.command()
def login(timeout: int = 180) -> None:
    """Log in to Spotify: opens your browser and waits for you to approve access."""
    init_db()
    asyncio.run(_run_login(timeout))


async def _run_login(timeout: int) -> None:
    parsed = urllib.parse.urlparse(settings.spotify_redirect_uri)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8000

    config = uvicorn.Config(login_app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())

    while not server.started:
        await asyncio.sleep(0.05)

    login_url = f"http://{host}:{port}/auth/login"
    typer.echo(f"Opening {login_url} in your browser...")
    webbrowser.open(login_url)

    try:
        await asyncio.wait_for(auth_module.login_complete.wait(), timeout=timeout)
        typer.echo("Logged in to Spotify.")
    except TimeoutError:
        typer.echo(f"Timed out after {timeout}s waiting for login.", err=True)
        raise typer.Exit(code=1) from None
    finally:
        server.should_exit = True
        await server_task


if __name__ == "__main__":
    cli()
