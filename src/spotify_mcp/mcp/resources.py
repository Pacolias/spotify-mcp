from spotify_mcp.mcp.server import mcp_server
from spotify_mcp.spotify.auth import NotAuthenticatedError
from spotify_mcp.spotify.client import get_currently_playing, get_playlist_tracks, list_playlists


@mcp_server.resource("spotify://me/now-playing", mime_type="application/json")
async def now_playing_resource() -> dict:
    """The track currently playing on the logged-in user's account, if any."""
    try:
        playing = await get_currently_playing()
    except NotAuthenticatedError as exc:
        return {"error": str(exc)}

    return playing or {"is_playing": False}


@mcp_server.resource("spotify://me/playlists", mime_type="application/json")
async def playlists_resource() -> dict:
    """The logged-in user's Spotify playlists."""
    try:
        results = await list_playlists(limit=50)
    except NotAuthenticatedError as exc:
        return {"error": str(exc)}

    return {"playlists": results}


@mcp_server.resource("spotify://playlist/{playlist_id}", mime_type="application/json")
async def playlist_resource(playlist_id: str) -> dict:
    """The tracks in a specific playlist."""
    try:
        results = await get_playlist_tracks(playlist_id, limit=100)
    except NotAuthenticatedError as exc:
        return {"error": str(exc)}

    return {"playlist_id": playlist_id, "tracks": results}
