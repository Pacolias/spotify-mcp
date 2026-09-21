# spotify-mcp

An MCP (Model Context Protocol) server for interacting with the Spotify Web API, built with Python and FastAPI.

This is a portfolio project — the engineering log below documents the architecture decisions as they're made, and why.

## Engineering log

### 2026-09-21 — MCP transport: streamable HTTP

Chose **streamable HTTP** over stdio for the MCP transport. stdio (the simpler default for local-only tools, where the host process spawns the server as a subprocess over stdin/stdout) would require whoever evaluates this project to run it locally with an MCP-compatible client. HTTP lets the server be deployed and evaluated without any local setup.

Trade-off accepted: HTTP transport means the server is network-reachable, so it needs its own auth layer (separate from Spotify's OAuth) to control who can talk to it — to be addressed when we get to that part.

### 2026-09-21 — MCP SDK: official Python SDK (`mcp` / `FastMCP`)

Using the [official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk), specifically `FastMCP`, its high-level API for declaring tools/resources with decorators. It exposes an ASGI app that mounts directly into the FastAPI app, so it composes naturally with the rest of the stack.

### 2026-09-21 — Spotify auth: OAuth2 Authorization Code + PKCE

Spotify auth uses OAuth2. Chose the **Authorization Code flow with PKCE** over the classic Authorization Code + client_secret flow — it's Spotify's current recommendation, and avoids having to carefully guard a long-lived client secret in favor of a per-flow dynamically generated verifier/challenge pair.

The OAuth callback (Spotify redirects the user's browser back after consent) is a regular route inside the same FastAPI app — this is needed regardless of which MCP transport is chosen, since the consent step always goes through a browser.

### 2026-09-21 — Token storage: database (SQLite to start)

Spotify access/refresh tokens are stored in a database rather than a flat file. SQLite to start (simple, zero external dependency), with an easy path to Postgres later if needed. Chosen over a JSON file mainly for persistence across restarts/redeploys on typical hosting setups, and because it better reflects real-world practice.

### 2026-09-21 — Dependency manager: uv

Using [uv](https://github.com/astral-sh/uv) (Astral) for dependency and virtualenv management, installed from Fedora's repos (`dnf install uv`). Chosen over Poetry and plain pip/venv for speed and because it's become the emerging standard in the Python/AI tooling ecosystem.

### 2026-09-21 — Spotify API access: raw httpx, no wrapper library

Calling the Spotify Web API directly with [httpx](https://www.python-httpx.org/) (async HTTP client) instead of a wrapper library like `spotipy`. More code to write ourselves, but it keeps the OAuth/PKCE flow and every API call fully transparent — useful both for learning MCP/OAuth properly and for showing that understanding in a portfolio project, rather than hiding it behind a third-party abstraction.

### 2026-09-21 — Database layer: SQLModel

Using [SQLModel](https://sqlmodel.tiangolo.com/) (by the FastAPI author, combines SQLAlchemy + Pydantic) over raw `sqlite3`. It's the current standard pairing for FastAPI + a database, integrates cleanly with FastAPI's Pydantic models, and isn't meaningfully more code than going raw for this project's scope.

### 2026-09-21 — MCP SDK API drift: `FastMCP` → `MCPServer`, and mounting gotcha

Two things worth logging because they weren't assumed, they were verified against the actually-installed `mcp` package (v2.x):

- The high-level API class was renamed from `FastMCP` to `MCPServer` (`mcp.server.mcpserver.MCPServer`) at some point after v1. Same shape (`.tool()` decorator, `.streamable_http_app()`), different import path.
- Mounting the MCP server's ASGI app into FastAPI with plain `app.mount("/mcp-server", mcp_server.streamable_http_app())` is not enough: FastAPI/Starlette does not forward `lifespan` events to mounted sub-apps, so the MCP session manager's task group never starts, and every request fails with `RuntimeError: Task group is not initialized`. Fixed by explicitly running `mcp_server.session_manager.run()` inside FastAPI's own `lifespan` context manager (see `src/spotify_mcp/main.py`).

Verified end-to-end with a real MCP client (`mcp.client.streamable_http`), not just an HTTP smoke test: connects, initializes the session, lists tools, and calls a `ping` tool successfully.

### 2026-09-21 — Spotify OAuth2 PKCE flow implemented

`/auth/login` and `/auth/callback` (in `src/spotify_mcp/spotify/auth.py`) implement the Authorization Code + PKCE flow decided earlier. Notes on the implementation:

- The initial OAuth scope is minimal: `user-read-currently-playing` only, needed for the first two tools (search, currently-playing — search itself needs no scope, any valid user token works for it). More scopes get added as more tools are built, following least privilege.
- The `state` parameter (CSRF protection, standard OAuth2) is mapped to its PKCE `code_verifier` in an **in-memory dict**, for the short window between redirect and callback. This is only safe because the app is single-user and single-process; a multi-worker deployment would need a shared store (DB/Redis) instead. Flagged here as a known simplification, not an oversight.
- Tokens are stored as a single fixed row (`id=1`) in the `spotifytoken` SQLite table via `session.merge()` (upsert by primary key) — consistent with the single-user design.
- `get_valid_access_token()` is the one function every Spotify-calling tool will use: it returns a token from the DB, transparently refreshing it first if it's within 30 seconds of expiring. Raises a custom `NotAuthenticatedError` (not an HTTP exception) if no login has happened yet, since it's meant to be called from MCP tool code, not just FastAPI routes.

Verified with a live request that `/auth/login` builds a correctly-formed redirect to Spotify's `/authorize` endpoint with all required PKCE params. The full round trip (actually logging in through the browser and completing `/auth/callback`) needs a human in the loop — can't be automated from here. Confirmed working against a real Spotify account.

Bug found and fixed while testing: SQLite has no timezone-aware datetime type, so a tz-aware `expires_at` written on login came back **naive** on read, and Python refuses to compare a naive and an aware datetime (`TypeError`). Fixed by working in naive-but-UTC datetimes consistently everywhere in `auth.py`.

### 2026-09-21 — First two MCP tools: `search_track` and `now_playing`

`src/spotify_mcp/spotify/client.py` wraps the two Spotify Web API calls (`GET /search`, `GET /me/player/currently-playing`) with `httpx`, using `get_valid_access_token()` for auth. `src/spotify_mcp/mcp/tools/search.py` and `.../playback.py` expose them as MCP tools (`search_track`, `now_playing`), registered by importing those modules at the bottom of `mcp/server.py` (after `mcp_server` is defined, to avoid a circular import).

Both tools return a formatted string rather than structured JSON — more directly useful for an LLM client to read and relay, and simple enough not to need a richer schema yet for just two read-only tools.

Verified end-to-end through a real MCP client, against a live Spotify account: `search_track` returns real catalog results, `now_playing` correctly returns "nothing playing" when idle and real track data when something is playing on the account.
