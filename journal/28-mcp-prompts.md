# Added MCP prompts: the third MCP primitive (build_playlist, listening_recap, import_youtube_mix)

**Date:** 2026-09-22

Tools (model-invoked actions) and resources (attachable read-only context) were already covered. **Prompts** are MCP's third primitive: reusable prompt templates a server exposes that a host can surface directly to the user (often as a "/"-style quick-access menu) — invoking one returns a pre-written message that kicks off a specific workflow, typically nudging the model toward a particular sequence of tool calls.

Checked the SDK's actual behavior before writing anything (as usual — API surface has drifted before): `@mcp_server.prompt()` infers arguments from the decorated function's signature (required if no default, same as tools), and a plain `str` return value is automatically wrapped as a single user-role `PromptMessage` — confirmed with a throwaway test prompt before writing the real ones.

Three prompts added (`src/spotify_mcp/mcp/prompts.py`), each one encoding a workflow this project had already done manually earlier in the same session:

- **`build_playlist(theme, num_songs=10, genre="")`** — encodes the lesson from [entry 24](24-youtube-playlist-import.md)/the "coding playlist" and "electronic coding" sessions: the prompt text explicitly tells the model to pick specific real songs from its own knowledge and verify the artist match, rather than searching Spotify with generic mood phrases (which was shown, live, to produce poor results).
- **`listening_recap()`** — points the model at the `spotify://me/dashboard` resource ([entry 27](27-profile-and-dashboard-resources.md)) for a one-read summary instead of chaining several tool calls.
- **`import_youtube_mix(youtube_url, playlist_name="")`** — a quick-access entry point to the `import_youtube_playlist` tool ([entry 24](24-youtube-playlist-import.md)).

Extended the existing "every X has a non-empty description" regression test ([entry 14](14-personal-data-tools.md), extended for resources in [entry 22](22-mcp-resources.md)) to also cover prompts — same f-string-docstring failure mode applies to any MCP primitive whose description comes from a docstring, not just tools.

Verified all three end-to-end through a real MCP client: listed with correct argument metadata (required vs. optional), and each one's rendered message was checked against real argument substitution (including the case where an optional argument is omitted and its clause is correctly left out, not rendered as an empty string).
