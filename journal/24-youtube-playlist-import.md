# `import_youtube_playlist`: build a Spotify playlist from a YouTube video's tracklist

**Date:** 2026-09-22

New capability, and a new domain for the project (YouTube, not just Spotify) — discussed and scoped explicitly before writing code, since it's a real architecture decision (new external dependency, new kind of data source).

**Scope decided up front**: read-only extraction from a video's chapters or description (for videos that already list their tracks — very common for mixes, "study playlist" videos, compilations), not audio fingerprinting/recognition. The audio-recognition path (download audio, detect track boundaries in a continuous mix, call a paid third-party recognition service) was explicitly considered and rejected as a much bigger, costlier project with its own reliability problems even for commercial tools — not something to fold into this one silently.

**Dependency**: [yt-dlp](https://github.com/yt-dlp/yt-dlp) for reading video metadata (title, description, chapters) without downloading video/audio. Chosen over the official YouTube Data API to avoid requiring a Google Cloud project + API key just for this — the trade-off is yt-dlp isn't an official API and can break if YouTube changes things.

**Implementation** (`src/spotify_mcp/youtube.py` + `mcp/tools/youtube.py`):
- `extract_tracklist(url)`: prefers the video's `chapters` (if the uploader added any — cleanest source, no parsing needed) and falls back to regex-parsing the description for two common tracklist shapes: `"0:00 Artist - Title"` (timestamp first) and `"Artist - Title (0:00)"` (timestamp last). Whichever pattern matches more lines wins, so a single stray time-like substring in an unrelated sentence doesn't get treated as a tracklist.
- `import_youtube_playlist` tool: extracts entries, searches each on Spotify (`search_tracks`), creates a new playlist, adds whatever matched, and reports back matched vs. unmatched.

**Real bug found by actually using it**, not by writing more unit tests first: the user asked to pull new songs from a real video (https://www.youtube.com/watch?v=JnaRmg8jd5k, 14 chapter entries) into their existing playlist. Several entries were explicitly labeled `"unreleased track"` / `"(coming soon)"` — tracks that don't exist on Spotify at all. `search_tracks` still returned *something* for them (Spotify search always returns a best-effort result), just a completely unrelated song by a different artist — four of those unreleased entries all matched the same wrong track. Blindly adding every match would have polluted a real playlist with wrong songs.

Fixed by adding `artist_plausibly_matches(entry, result_artists)`: parses the artist token(s) from the tracklist entry's `"Artist - Title"` shape and requires loose containment against the Spotify result's artist list before accepting a match. An entry with no parseable artist (a bare chapter marker like `"LOOP"`, not a real track at all) is never accepted either. Verified against the exact real scenario: of the 14 real entries, 7 correctly matched (including 4 legitimately new tracks not yet in the target playlist) and 7 were correctly rejected — 4 duplicate false matches to one wrong song, one to an unrelated artist via a generic word ("lithium" → Evanescence), one to another unrelated artist, and the non-track "LOOP" marker.

Before writing to the real playlist, the diff (already-have / new-and-confident / rejected) was shown to the user for confirmation rather than applied silently — the first time this project mutated a *real*, already-populated playlist based on a fuzzy/heuristic process, as opposed to a disposable test playlist.

Verified end-to-end twice: once via direct function calls against the user's real playlist (which is how the actual request got fulfilled — 3→7 tracks, confirmed correct), and again through the registered MCP tool over a real stdio connection against a disposable test playlist, to prove the *tool* itself (not just the underlying functions) behaves the same way.
