# First two MCP tools: `search_track` and `now_playing`

**Date:** 2026-09-21

`src/spotify_mcp/spotify/client.py` wraps the two Spotify Web API calls (`GET /search`, `GET /me/player/currently-playing`) with `httpx`, using `get_valid_access_token()` for auth. `src/spotify_mcp/mcp/tools/search.py` and `.../playback.py` expose them as MCP tools (`search_track`, `now_playing`), registered by importing those modules at the bottom of `mcp/server.py` (after `mcp_server` is defined, to avoid a circular import).

Both tools return a formatted string rather than structured JSON — more directly useful for an LLM client to read and relay, and simple enough not to need a richer schema yet for just two read-only tools.

Verified end-to-end through a real MCP client, against a live Spotify account: `search_track` returns real catalog results, `now_playing` correctly returns "nothing playing" when idle and real track data when something is playing on the account.
