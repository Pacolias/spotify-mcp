# Playback control tools: pause, resume, skip, volume, queue

**Date:** 2026-09-21

Final category of the planned tool set: `pause`, `resume`, `skip_next`, `skip_previous`, `set_playback_volume`, `queue_track`. The most delicate category so far — these are the first tools with an *immediate, audible* real-world effect (previous write tools, like creating a playlist, changed data; these change what's playing right now on a real device).

Given that, and given this project's track record of the documented Spotify API shape not always matching reality (see entries 13 and 15), each endpoint was checked against the real API — with the user's explicit go-ahead first, since it meant actually pausing/resuming/skipping their live playback — before writing any tool code:

```
PUT  /me/player/pause                          -> 200 (plain-text snapshot id body, not JSON)
PUT  /me/player/play                           -> 200 (same)
POST /me/player/next                           -> 200 (same)
POST /me/player/previous                       -> 200 (same)
PUT  /me/player/volume?volume_percent=N        -> 204
POST /me/player/queue?uri=spotify:track:{id}   -> 200 (same)
```

Interesting, minor find: most of these return `200` with a **plain-text** snapshot-id-style body (not JSON, and not the `204 No Content` some Spotify docs describe for a few of these). Doesn't affect the code — none of these responses are parsed, only `raise_for_status()` is checked — but worth noting since it's a further small mismatch from the documented shape.

Also found: `GET /me/player` (full player state) returns `401 Permissions missing` with the scopes this project requests — it needs `user-read-playback-state`, which wasn't requested (only `user-read-currently-playing`, used for the narrower `now_playing` tool, was). Not needed for anything currently planned, so left unrequested rather than adding a scope for an endpoint nothing uses yet.

`set_playback_volume` validates `volume_percent` is between 0 and 100 before calling Spotify at all, returning a plain error string rather than letting a bad value hit the API.

Verified end-to-end against the user's real, live playback, with explicit confirmation from the user first: paused and resumed real audio (confirmed audibly by the user), skipped forward and back a track, changed volume, and queued a real track — all through the actual MCP tools over a live MCP client connection, not just the underlying client functions.

**This completes the four-category tool-expansion plan** (composed tools → dropped, see entry 13; personal data; playlists; playback control). The project now has 16 MCP tools total.
