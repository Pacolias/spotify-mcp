# `public=False` on playlist creation: confirmed Spotify-side bug, not fixable here

**Date:** 2026-09-22

[Journal entry 15](15-playlist-endpoints-renamed.md) flagged but never root-caused that `create_playlist(..., public=False)` was observed creating public playlists anyway. Picked this up as the first item of a "what could we improve" pass, since it's the only known behavioral defect in the project.

**Two hypotheses considered before touching code**, since this could plausibly be either our bug or Spotify's:

1. **Stale OAuth scope.** The `playlist-modify-private`/`playlist-modify-public` scopes were only added in [entry 14](14-personal-data-tools.md); if the stored token in `spotify_mcp.db` predated that change, a refreshed token wouldn't retroactively gain the new scope (refresh tokens don't acquire scopes they weren't originally granted — only a fresh login/consent does). Checked directly against the local SQLite DB: the stored token's `scope` column already includes both. Ruled out.
2. **Genuine Spotify API bug**, independent of scope. Confirmed by web search: multiple threads on the Spotify for Developers community forum report the exact same symptom, and Spotify's own "Change Playlist Details" endpoint (the documented way to flip visibility after creation) has the same reported issue — accepts the `public: false` write with no error, but doesn't apply it.

**Reproduced live** rather than trusting the forum reports alone: called `create_user_playlist` with `public=false` against the real account (full scope already granted) — playlist `0Ijhf5tNKeV8Wxvhc1S1bu` was created and immediately listed back as `public`. Also checked whether a follow-up `PUT /playlists/{id}` (change-playlist-details) after creation could work around it — per the same community reports, that endpoint silently no-ops the `public` field too, so there's no reliable client-side fix.

**Conclusion**: this is not our bug and can't be fixed from this codebase. Documented instead of silently leaving `public=False` looking functional:
- Docstring warnings on `create_user_playlist` and `import_youtube_playlist` (both take `public`).
- A code comment at the `create_playlist` call site in `spotify/client.py` explaining what was checked and why it's left as-is.
- README tool table flags both affected tools.

**Cleanup note**: the test playlist created during reproduction (`spotify-mcp test — delete me (public bug check)`, id `0Ijhf5tNKeV8Wxvhc1S1bu`) needs to be removed manually via the Spotify app — there's no `delete_playlist`/`unfollow_playlist` tool in this project (Spotify's API only supports "unfollow," which isn't exposed here), so it can't be cleaned up from the MCP server itself.
