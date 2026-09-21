# Engineering journal

Chronological log of architecture decisions and notable findings for `spotify-mcp`, one entry per file. See the [project README](../README.md) for the current state of the project.

1. [MCP transport: streamable HTTP](01-mcp-transport-streamable-http.md)
2. [MCP SDK: official Python SDK](02-mcp-sdk-choice.md)
3. [Spotify auth: OAuth2 Authorization Code + PKCE](03-spotify-oauth-flow-choice.md)
4. [Token storage: database (SQLite to start)](04-token-storage-database.md)
5. [Dependency manager: uv](05-dependency-manager-uv.md)
6. [Spotify API access: raw httpx, no wrapper library](06-spotify-api-access-httpx.md)
7. [Database layer: SQLModel](07-database-layer-sqlmodel.md)
8. [MCP SDK API drift: `FastMCP` → `MCPServer`, and mounting gotcha](08-mcp-sdk-api-drift-and-mounting-gotcha.md)
9. [Spotify OAuth2 PKCE flow implemented](09-spotify-oauth-pkce-implemented.md)
10. [First two MCP tools: `search_track` and `now_playing`](10-first-mcp-tools-search-and-playback.md)
11. [Test suite: pytest + pytest-asyncio + respx](11-test-suite.md)
12. [Deployment target: Render, plus bearer-token auth on the MCP endpoint](12-deployment-plan-and-mcp-bearer-auth.md)
13. [Spotify's "discovery" endpoints are restricted for new apps — composed tools plan dropped](13-recommendation-endpoints-restricted.md)
