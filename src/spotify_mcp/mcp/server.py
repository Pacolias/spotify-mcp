from mcp.server.mcpserver import MCPServer

mcp_server = MCPServer("spotify-mcp")


@mcp_server.tool()
def ping() -> str:
    """Health-check tool: confirms the MCP server is reachable and tools can be called."""
    return "pong"


# Importing these registers their @mcp_server.tool()-decorated functions above.
# Must stay at the bottom: each module imports `mcp_server` from this file,
# so it needs to already be defined when they're imported.
from spotify_mcp.mcp.tools import playback, search  # noqa: E402, F401
