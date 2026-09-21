# Test suite: pytest + pytest-asyncio + respx

**Date:** 2026-09-21

Testing stack: **pytest** (the de facto standard for Python), **pytest-asyncio** (`asyncio_mode = "auto"` in `pyproject.toml`, so `async def test_...` functions just work without a decorator on each one), and **respx** for mocking `httpx` calls to the Spotify API — chosen over manual monkeypatching since it's the standard mocking library built specifically for `httpx` (same maintainers), and keeps test code focused on request/response shape instead of patching internals by hand.

**Database isolation**: tests never touch the real `spotify_mcp.db` (which holds a real Spotify token). A `db_engine` fixture (`tests/conftest.py`) creates a throwaway SQLite database per test and monkeypatches the `engine` name in both `spotify_mcp.db.session` and `spotify_mcp.spotify.auth`. Two patch targets are needed, not one: `auth.py` does `from spotify_mcp.db.session import engine`, which binds its own local reference at import time — patching `db_session.engine` alone wouldn't reach it. A `logged_in` fixture layers on top to seed a valid token for tests that exercise Spotify-API-backed code.

**Coverage so far** (10 tests):
- `test_pkce.py` — the PKCE `code_verifier`/`code_challenge` helpers are pure functions, tested directly against the spec's derivation (`base64url(sha256(verifier))`), not just "produces *a* string".
- `test_auth.py` — `get_valid_access_token()`'s three real behaviors: raises `NotAuthenticatedError` with no token, returns an unexpired token as-is, and refreshes (via a mocked Spotify token endpoint) when close to expiry — including that the refreshed token is actually persisted back to the DB.
- `test_spotify_client.py` — `search_tracks` and `get_currently_playing` against mocked Spotify Web API responses, including the "nothing playing" 204 case.
- `test_health.py` — one FastAPI integration test (`TestClient`) confirming the app itself boots (lifespan runs cleanly) and `/health` responds.

Not yet tested: the MCP tools themselves (`search_track`, `now_playing`) end-to-end through the MCP protocol, and the `/auth/login`/`/auth/callback` routes — those were verified manually against a real Spotify account instead (see [entry 09](09-spotify-oauth-pkce-implemented.md)). Automating the full OAuth browser round-trip isn't practical; the MCP-tool-level integration test is a reasonable gap to close later if the tool count grows.
