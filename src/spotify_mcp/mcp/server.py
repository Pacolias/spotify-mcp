from mcp.server.mcpserver import MCPServer

mcp_server = MCPServer("spotify-mcp")


@mcp_server.tool()
def ping() -> str:
    """Health-check tool: confirms the MCP server is reachable and tools can be called."""
    return "pong"
