from spotify_mcp.mcp.server import mcp_server
from spotify_mcp.spotify.auth import NotAuthenticatedError
from spotify_mcp.spotify.client import add_tracks_to_playlist, create_playlist, search_tracks
from spotify_mcp.youtube import artist_plausibly_matches, extract_tracklist


@mcp_server.tool()
async def import_youtube_playlist(
    youtube_url: str, playlist_name: str, description: str = "", public: bool = False
) -> str:
    """Extract a tracklist from a YouTube video's chapters or description
    (for videos that list their songs — mixes, compilations, study/focus
    playlists, etc.), look each one up on Spotify, and add whatever matches
    to a new playlist. Best-effort: only works for videos with a written
    tracklist (no audio recognition); entries are skipped rather than
    guessed when the Spotify result's artist doesn't match the tracklist
    entry's artist (common for "unreleased"/"coming soon" tracks that
    aren't on Spotify at all).

    ⚠️ `public=False` is currently ignored by Spotify's API — playlists are
    created public regardless (confirmed bug on Spotify's side, not this
    server; see journal entry 30)."""
    try:
        entries = extract_tracklist(youtube_url)
    except Exception as exc:  # yt-dlp raises its own broad exception types
        return f"Couldn't read that YouTube video: {exc}"

    if not entries:
        return "No tracklist found in this video's chapters or description."

    matched_ids = []
    matched_names = []
    unmatched = []
    try:
        for entry in entries:
            results = await search_tracks(entry, limit=1)
            if results and artist_plausibly_matches(entry, results[0]["artists"]):
                matched_ids.append(results[0]["id"])
                matched_names.append(f"{results[0]['name']} — {', '.join(results[0]['artists'])}")
            else:
                unmatched.append(entry)
    except NotAuthenticatedError as exc:
        return str(exc)

    if not matched_ids:
        return f"Found {len(entries)} tracklist entries but none matched on Spotify."

    try:
        playlist = await create_playlist(playlist_name, description=description, public=public)
        await add_tracks_to_playlist(playlist["id"], matched_ids)
    except NotAuthenticatedError as exc:
        return str(exc)

    lines = [
        f"Created '{playlist['name']}' with {len(matched_ids)}/{len(entries)} "
        f"tracks matched — {playlist['url']}",
        "",
        "Matched:",
        *[f"  {name}" for name in matched_names],
    ]
    if unmatched:
        lines += ["", "No confident Spotify match:", *[f"  {entry}" for entry in unmatched]]

    return "\n".join(lines)
