# Two more prompts: `start_listening`, `curate_from_liked` — and a real pagination gap they surfaced

**Date:** 2026-09-22

Two more prompts, on top of the three from [entry 28](28-mcp-prompts.md):

- **`start_listening(device_hint="")`** — encodes the "get me listening" workflow discussed in [entry 26](26-device-listing-and-activation.md): check `now_playing` first, and only if nothing's active, use `list_devices` + `activate_device`. Explicitly tells the model to ask the user when there's more than one reasonable device rather than guessing, and to say so plainly if `list_devices` comes back empty — reinforcing that this server can't launch Spotify itself, it can only activate something already running.
- **`curate_from_liked(criteria, num_songs=15, playlist_name="")`** — build a themed playlist out of the user's existing Liked Songs rather than new searches.

Writing `curate_from_liked` surfaced a real gap before it even got used: `liked_songs` had no `offset` parameter, only `limit`. Checked against the real account — **3,706 saved tracks**, and Spotify caps `limit` at 50 per call (`limit=100` outright `400`s with `"Invalid limit"`). Without pagination, `curate_from_liked` could only ever see the first 20 (the tool's default) or 50 (its cap) tracks — nowhere near enough to meaningfully curate a themed playlist from a library that size. Added `offset` to both `get_saved_tracks` and the `liked_songs` tool, and the prompt now explicitly tells the model to page through in 50-track batches with increasing offsets before picking.

Verified end-to-end: pagination confirmed live (two calls with `offset=0` and `offset=3` returned genuinely different tracks from the real library), and both new prompts confirmed through a real MCP client — argument substitution correct, including the conditional device-hint clause in `start_listening` being present only when given.
