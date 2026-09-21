from spotify_mcp.mcp.server import mcp_server
from spotify_mcp.spotify.auth import NotAuthenticatedError
from spotify_mcp.spotify.client import (
    SpotifyAPIError,
    get_saved_tracks,
    remove_saved_tracks,
    save_tracks,
)


@mcp_server.tool()
async def liked_songs(limit: int = 20, offset: int = 0) -> str:
    """List the user's saved ("Liked Songs") tracks. limit is capped at 50
    by Spotify — pass a higher offset in a follow-up call to page through
    more (the user may have hundreds or thousands of saved tracks)."""
    try:
        results = await get_saved_tracks(limit=limit, offset=offset)
    except NotAuthenticatedError as exc:
        return str(exc)

    if not results:
        return "No liked songs found."

    return "\n".join(f"{t['name']} — {', '.join(t['artists'])} — id: {t['id']}" for t in results)


@mcp_server.tool()
async def like_tracks(track_ids: list[str]) -> str:
    """Save one or more tracks to the user's Liked Songs. track_ids come
    from search_track / playlist_tracks / top_tracks. Note: Spotify
    restricts this endpoint to apps with "Extended Quota Mode" approval —
    it may fail with a permissions error on apps that don't have it."""
    try:
        await save_tracks(track_ids)
    except NotAuthenticatedError as exc:
        return str(exc)
    except SpotifyAPIError as exc:
        return f"Spotify API error: {exc}"
    return f"Saved {len(track_ids)} track(s) to Liked Songs."


@mcp_server.tool()
async def unlike_tracks(track_ids: list[str]) -> str:
    """Remove one or more tracks from the user's Liked Songs. Note: Spotify
    restricts this endpoint to apps with "Extended Quota Mode" approval —
    it may fail with a permissions error on apps that don't have it."""
    try:
        await remove_saved_tracks(track_ids)
    except NotAuthenticatedError as exc:
        return str(exc)
    except SpotifyAPIError as exc:
        return f"Spotify API error: {exc}"
    return f"Removed {len(track_ids)} track(s) from Liked Songs."
