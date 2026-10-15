import typer
import uvicorn

cli = typer.Typer(
    name="spotify-mcp",
    help="Remote MCP server for the Spotify Web API.",
    add_completion=False,
    no_args_is_help=True,
)


@cli.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the MCP server over streamable HTTP, with OAuth."""
    uvicorn.run("spotify_mcp.main:app", host=host, port=port)


# A Typer app with a single command runs it without naming it; this keeps
# `serve` an explicit subcommand.
@cli.callback()
def main() -> None:
    pass


if __name__ == "__main__":
    cli()
