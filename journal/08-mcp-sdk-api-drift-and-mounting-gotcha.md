# MCP SDK API drift: `FastMCP` → `MCPServer`, and mounting gotcha

**Date:** 2026-09-21

Two things worth logging because they weren't assumed, they were verified against the actually-installed `mcp` package (v2.x):

- The high-level API class was renamed from `FastMCP` to `MCPServer` (`mcp.server.mcpserver.MCPServer`) at some point after v1. Same shape (`.tool()` decorator, `.streamable_http_app()`), different import path.
- Mounting the MCP server's ASGI app into FastAPI with plain `app.mount("/mcp-server", mcp_server.streamable_http_app())` is not enough: FastAPI/Starlette does not forward `lifespan` events to mounted sub-apps, so the MCP session manager's task group never starts, and every request fails with `RuntimeError: Task group is not initialized`. Fixed by explicitly running `mcp_server.session_manager.run()` inside FastAPI's own `lifespan` context manager (see `src/spotify_mcp/main.py`).

Verified end-to-end with a real MCP client (`mcp.client.streamable_http`), not just an HTTP smoke test: connects, initializes the session, lists tools, and calls a `ping` tool successfully.
