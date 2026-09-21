from spotify_mcp.mcp.server import mcp_server
from spotify_mcp.spotify.auth import NotAuthenticatedError
from spotify_mcp.spotify.client import (
    add_to_queue,
    get_currently_playing,
    pause_playback,
    resume_playback,
    set_volume,
    skip_to_next,
    skip_to_previous,
)


@mcp_server.tool()
async def now_playing() -> str:
    """Get the track currently playing on the user's Spotify account, if any."""
    try:
        playing = await get_currently_playing()
    except NotAuthenticatedError as exc:
        return str(exc)

    if playing is None:
        return "Nothing is currently playing."

    status = "Playing" if playing["is_playing"] else "Paused"
    return (
        f"{status}: {playing['name']} — {', '.join(playing['artists'])} "
        f"({playing['album']}): {playing['url']}"
    )


@mcp_server.tool()
async def pause() -> str:
    """Pause playback on the user's active Spotify device."""
    try:
        await pause_playback()
    except NotAuthenticatedError as exc:
        return str(exc)
    return "Paused."


@mcp_server.tool()
async def resume() -> str:
    """Resume/start playback on the user's active Spotify device."""
    try:
        await resume_playback()
    except NotAuthenticatedError as exc:
        return str(exc)
    return "Resumed playback."


@mcp_server.tool()
async def skip_next() -> str:
    """Skip to the next track on the user's active Spotify device."""
    try:
        await skip_to_next()
    except NotAuthenticatedError as exc:
        return str(exc)
    return "Skipped to next track."


@mcp_server.tool()
async def skip_previous() -> str:
    """Skip to the previous track on the user's active Spotify device."""
    try:
        await skip_to_previous()
    except NotAuthenticatedError as exc:
        return str(exc)
    return "Skipped to previous track."


@mcp_server.tool()
async def set_playback_volume(volume_percent: int) -> str:
    """Set playback volume on the user's active Spotify device. volume_percent: 0-100."""
    if not 0 <= volume_percent <= 100:
        return "volume_percent must be between 0 and 100."
    try:
        await set_volume(volume_percent)
    except NotAuthenticatedError as exc:
        return str(exc)
    return f"Volume set to {volume_percent}%."


@mcp_server.tool()
async def queue_track(track_id: str) -> str:
    """Add a track to the playback queue. track_id comes from search_track."""
    try:
        await add_to_queue(track_id)
    except NotAuthenticatedError as exc:
        return str(exc)
    return "Track added to queue."
