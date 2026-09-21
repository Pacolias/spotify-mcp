from spotify_mcp.db.session import init_db
from spotify_mcp.mcp.server import mcp_server


def main() -> None:
    init_db()
    mcp_server.run()  # defaults to transport="stdio"


if __name__ == "__main__":
    main()
