from mcp.server.mcpserver import MCPServer

mcp_server = MCPServer("spotify-mcp")


@mcp_server.tool()
def ping() -> str:
    """Health-check tool: confirms the MCP server is reachable and tools can be called."""
    return "pong"


# Importing these registers their @mcp_server.tool()/@mcp_server.resource()
# -decorated functions above. Must stay at the bottom: each module imports
# `mcp_server` from this file, so it needs to already be defined first.
from spotify_mcp.mcp import resources  # noqa: E402, F401
from spotify_mcp.mcp.tools import (  # noqa: E402, F401
    library,
    playback,
    personal,
    playlists,
    search,
    youtube,
)
