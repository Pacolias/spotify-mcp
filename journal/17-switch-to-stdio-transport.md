# Reversed decision: MCP transport switched from streamable HTTP to stdio

**Date:** 2026-09-21

After using the project for a while, decided this should be a **local-only tool run via stdio**, not a deployed HTTP service. This directly reverses [entry 01](01-mcp-transport-streamable-http.md), and invalidates two things that were built on top of that original choice:

- **The Render deployment plan** ([entry 12](12-deployment-plan-and-mcp-bearer-auth.md)) is dropped. A stdio server only runs as a subprocess spawned by an MCP host (Claude Desktop, Claude Code) on the same machine — there's nothing to deploy to a remote host.
- **The bearer-token auth middleware** on the MCP endpoint, also from entry 12, is removed entirely (`src/spotify_mcp/mcp/auth.py`, `MCP_BEARER_TOKEN`, its tests). It existed specifically because HTTP made the MCP server network-reachable; stdio has no network exposure to guard.

**Trade-off made explicit before implementing**: the original reason for choosing HTTP was this being a portfolio project — a Tech Lead could open a URL without any local setup. Stdio gives that up: evaluating this project now requires cloning the repo and running it locally. Flagged clearly to the user before making the change; they confirmed this is the trade-off they want.

**What stays the same**: the Spotify OAuth2 + PKCE login flow still needs a browser and a local HTTP endpoint for the callback — that's a property of OAuth's redirect-based consent flow, not of the MCP transport, and was already anticipated back in entry 01 and entry 03. Decided to keep this as a **separate FastAPI app, run independently from the MCP server**, rather than folding a temporary HTTP listener into the stdio process itself — two single-purpose processes instead of one process juggling two protocols.

**Resulting architecture:**
- `src/spotify_mcp/main.py` — a small FastAPI app with only `/auth/login`, `/auth/callback`, and `/health`. Run once (or whenever a re-login is needed) via `uv run uvicorn spotify_mcp.main:app`.
- `src/spotify_mcp/stdio_server.py` — the actual MCP server entrypoint, `mcp_server.run()` over stdio. Registered as an installable console script (`spotify-mcp`, via `[project.scripts]` in `pyproject.toml`) so an MCP host can be pointed at it directly instead of a raw Python invocation.

Verified end-to-end: the login server still starts and its `/auth/login`/`/health` routes work with the MCP mount and bearer middleware removed; the stdio server was exercised with a real stdio MCP client (`mcp.client.stdio`) spawning `uv run spotify-mcp` as a subprocess — connected, listed all 16 tools, and called `now_playing` successfully, which itself round-tripped through token refresh and a real Spotify API call. Full test suite (25 tests, down from 28 after removing the three bearer-auth-specific tests) passes.
