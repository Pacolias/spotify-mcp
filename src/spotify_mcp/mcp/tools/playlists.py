from spotify_mcp.mcp.server import mcp_server
from spotify_mcp.spotify.auth import NotAuthenticatedError
from spotify_mcp.spotify.client import (
    add_tracks_to_playlist,
    create_playlist,
    get_playlist_tracks,
    list_playlists,
)


@mcp_server.tool()
async def list_user_playlists(limit: int = 20) -> str:
    """List the logged-in user's Spotify playlists."""
    try:
        results = await list_playlists(limit=limit)
    except NotAuthenticatedError as exc:
        return str(exc)

    if not results:
        return "No playlists found."

    return "\n".join(
        f"{p['name']} ({p['track_count']} tracks, {'public' if p['public'] else 'private'}) — id: {p['id']}"
        for p in results
    )


@mcp_server.tool()
async def playlist_tracks(playlist_id: str, limit: int = 50) -> str:
    """List the tracks in a playlist, including each track's id (needed by
    add_tracks / remove_tracks_from_playlist). playlist_id comes from
    list_user_playlists."""
    try:
        results = await get_playlist_tracks(playlist_id, limit=limit)
    except NotAuthenticatedError as exc:
        return str(exc)

    if not results:
        return "This playlist has no tracks."

    return "\n".join(
        f"{t['name']} — {', '.join(t['artists'])} — id: {t['id']}" for t in results
    )


@mcp_server.tool()
async def create_user_playlist(name: str, description: str = "", public: bool = False) -> str:
    """Create a new playlist in the logged-in user's Spotify account."""
    try:
        playlist = await create_playlist(name, description=description, public=public)
    except NotAuthenticatedError as exc:
        return str(exc)

    return f"Created playlist '{playlist['name']}' — id: {playlist['id']} — {playlist['url']}"


@mcp_server.tool()
async def add_tracks(playlist_id: str, track_ids: list[str]) -> str:
    """Add one or more tracks to a playlist. playlist_id and track_ids come
    from create_user_playlist / list_user_playlists and search_track."""
    try:
        await add_tracks_to_playlist(playlist_id, track_ids)
    except NotAuthenticatedError as exc:
        return str(exc)

    return f"Added {len(track_ids)} track(s) to playlist {playlist_id}."
