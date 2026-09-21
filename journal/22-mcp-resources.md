# Added MCP resources: now-playing, playlists, playlist/{id}

**Date:** 2026-09-22

Until now the project only used **tools** (functions the model actively decides to call). MCP has a second primitive, **resources**: read-only, URI-addressed data that a host lists (`resources/list`) and reads (`resources/read`), meant to be attached to context more like a referenced document than an invoked action. Added three, all read-only — write actions stay tools, resources shouldn't have side effects:

- `spotify://me/now-playing`
- `spotify://me/playlists`
- `spotify://playlist/{playlist_id}` — a **resource template** (parameterized URI); the SDK binds `{playlist_id}` straight to the decorated function's argument, same mechanism as a tool's parameters.

**Format decision**: resources return structured JSON (`mime_type="application/json"`, returning a plain `dict`) rather than the human-formatted strings tools use. A resource is closer to an attached document than a conversational answer, so JSON is more reusable — and convenient: the SDK auto-serializes a returned `dict` to JSON when the resource declares that mime type, no manual `json.dumps()` needed (confirmed by testing a plain dict return before writing the real resources).

Implementation lives in a single new module, `mcp/resources.py` (not a `resources/` package like `mcp/tools/`) — three resources didn't justify a package, unlike the tools, which are split by domain (search, playback, personal, playlists) because there are many more of them.

Extended the existing "every tool has a description" regression test ([entry 14](14-personal-data-tools.md)) to also cover resources and resource templates — same f-string-docstring risk applies to any docstring-driven MCP primitive, not just tools.

Verified end-to-end through a real stdio MCP client: `list_resources`/`list_resource_templates` show all three with the right mime type; reading each returns real, correctly-shaped JSON from the live Spotify account, including the templated `spotify://playlist/{playlist_id}` resolving a real playlist's tracks.
