# Personal data tools: top_tracks, top_artists, recently_played

**Date:** 2026-09-21

Expanded the requested OAuth scopes to cover the rest of the planned build (personal data, playlists, playback control) in one go — `user-top-read`, `user-read-recently-played`, `playlist-read-private`, `playlist-modify-private`, `playlist-modify-public`, `user-modify-playback-state` — so the user only has to re-login through the browser once for the rest of this phase, instead of once per category.

Before writing any tool code, the underlying endpoints (`/me/top/tracks`, `/me/top/artists`, `/me/player/recently-played`, `/me/playlists`) were checked live with the newly-scoped token and all returned `200` — confirming these are gated by scope only, not by the app-tier restriction found in [entry 13](13-recommendation-endpoints-restricted.md).

Added `get_top_tracks`, `get_top_artists`, `get_recently_played` to `spotify/client.py`, and three matching MCP tools in `mcp/tools/personal.py`: `top_tracks`, `top_artists`, `recently_played`. `top_tracks`/`top_artists` take a `time_range` (`short_term` ~4 weeks, `medium_term` ~6 months default, `long_term` years).

**Bug caught before it shipped**: the first draft used an f-string as the docstring for `top_tracks`/`top_artists`, to interpolate the shared `time_range` explanation. An f-string as a function's first statement is **not** a real docstring to Python — `__doc__` comes back `None`, since f-strings compile differently from plain string literals. That would have silently shipped two tools with no description visible to the model. Caught by inspecting the actual registered tool descriptions over a live MCP connection rather than assuming the code worked, and fixed by writing the explanation as a plain (non-f) docstring instead. Added `tests/test_mcp_tool_registration.py` as a standing regression test: it iterates every registered tool and asserts none has an empty description, so this class of bug fails a test run instead of shipping silently in the future.
