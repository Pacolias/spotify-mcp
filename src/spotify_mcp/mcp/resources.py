from collections.abc import Coroutine
from typing import Any

from spotify_mcp.mcp.server import mcp_server
from spotify_mcp.spotify.auth import NotAuthenticatedError
from spotify_mcp.spotify.client import (
    get_current_user_profile,
    get_currently_playing,
    get_devices,
    get_playlist_tracks,
    get_recently_played,
    get_top_tracks,
    list_playlists,
)


@mcp_server.resource("spotify://me/now-playing", mime_type="application/json")
async def now_playing_resource() -> dict[str, Any]:
    """The track currently playing on the logged-in user's account, if any."""
    try:
        playing = await get_currently_playing()
    except NotAuthenticatedError as exc:
        return {"error": str(exc)}

    return playing or {"is_playing": False}


@mcp_server.resource("spotify://me/playlists", mime_type="application/json")
async def playlists_resource() -> dict[str, Any]:
    """The logged-in user's Spotify playlists."""
    try:
        results = await list_playlists(limit=50)
    except NotAuthenticatedError as exc:
        return {"error": str(exc)}

    return {"playlists": results}


@mcp_server.resource("spotify://playlist/{playlist_id}", mime_type="application/json")
async def playlist_resource(playlist_id: str) -> dict[str, Any]:
    """The tracks in a specific playlist."""
    try:
        results = await get_playlist_tracks(playlist_id, limit=100)
    except NotAuthenticatedError as exc:
        return {"error": str(exc)}

    return {"playlist_id": playlist_id, "tracks": results}


@mcp_server.resource("spotify://me/profile", mime_type="application/json")
async def profile_resource() -> dict[str, Any]:
    """The logged-in user's basic Spotify profile (id, display name,
    follower count, profile URL/image)."""
    try:
        return await get_current_user_profile()
    except NotAuthenticatedError as exc:
        return {"error": str(exc)}


async def _best_effort(coro: Coroutine[Any, Any, Any]) -> Any:
    # Used only by dashboard_resource below: one section failing (e.g. no
    # devices reachable) shouldn't blank out the whole snapshot.
    try:
        return await coro
    except Exception:
        return None


@mcp_server.resource("spotify://me/dashboard", mime_type="application/json")
async def dashboard_resource() -> dict[str, Any]:
    """A one-shot snapshot of the user's Spotify state — what's playing,
    available devices, top tracks, and recently played — everything a host
    might want to show at a glance, without several separate tool calls."""
    try:
        now_playing = await get_currently_playing()
    except NotAuthenticatedError as exc:
        return {"error": str(exc)}

    return {
        "now_playing": now_playing or {"is_playing": False},
        "devices": await _best_effort(get_devices()),
        "top_tracks": await _best_effort(get_top_tracks(limit=5)),
        "recently_played": await _best_effort(get_recently_played(limit=5)),
    }
