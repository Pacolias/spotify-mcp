from spotify_mcp.mcp.server import mcp_server
from spotify_mcp.spotify.auth import NotAuthenticatedError
from spotify_mcp.spotify.client import (
    SpotifyAPIError,
    SpotifyPlaybackError,
    add_to_queue,
    get_currently_playing,
    get_devices,
    pause_playback,
    resume_playback,
    seek_to_position,
    set_repeat_mode,
    set_shuffle,
    set_volume,
    skip_to_next,
    skip_to_previous,
    transfer_playback,
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
    except (NotAuthenticatedError, SpotifyPlaybackError) as exc:
        return str(exc)
    return "Paused."


@mcp_server.tool()
async def resume() -> str:
    """Resume/start playback on the user's active Spotify device."""
    try:
        await resume_playback()
    except (NotAuthenticatedError, SpotifyPlaybackError) as exc:
        return str(exc)
    return "Resumed playback."


@mcp_server.tool()
async def skip_next() -> str:
    """Skip to the next track on the user's active Spotify device."""
    try:
        await skip_to_next()
    except (NotAuthenticatedError, SpotifyPlaybackError) as exc:
        return str(exc)
    return "Skipped to next track."


@mcp_server.tool()
async def skip_previous() -> str:
    """Skip to the previous track on the user's active Spotify device."""
    try:
        await skip_to_previous()
    except (NotAuthenticatedError, SpotifyPlaybackError) as exc:
        return str(exc)
    return "Skipped to previous track."


@mcp_server.tool()
async def set_playback_volume(volume_percent: int) -> str:
    """Set playback volume on the user's active Spotify device. volume_percent: 0-100."""
    if not 0 <= volume_percent <= 100:
        return "volume_percent must be between 0 and 100."
    try:
        await set_volume(volume_percent)
    except (NotAuthenticatedError, SpotifyPlaybackError) as exc:
        return str(exc)
    return f"Volume set to {volume_percent}%."


@mcp_server.tool()
async def queue_track(track_id: str) -> str:
    """Add a track to the playback queue. track_id comes from search_track."""
    try:
        await add_to_queue(track_id)
    except (NotAuthenticatedError, SpotifyPlaybackError) as exc:
        return str(exc)
    return "Track added to queue."


@mcp_server.tool()
async def shuffle(enabled: bool) -> str:
    """Turn shuffle mode on or off on the user's active Spotify device."""
    try:
        await set_shuffle(enabled)
    except (NotAuthenticatedError, SpotifyPlaybackError) as exc:
        return str(exc)
    return f"Shuffle {'on' if enabled else 'off'}."


@mcp_server.tool()
async def repeat_mode(mode: str) -> str:
    """Set repeat mode on the user's active Spotify device. mode: "track"
    (repeat the current track), "context" (repeat the current playlist/album),
    or "off"."""
    if mode not in ("track", "context", "off"):
        return "mode must be one of: track, context, off."
    try:
        await set_repeat_mode(mode)
    except (NotAuthenticatedError, SpotifyPlaybackError) as exc:
        return str(exc)
    return f"Repeat mode set to '{mode}'."


@mcp_server.tool()
async def seek(position_ms: int) -> str:
    """Seek to a position (in milliseconds) in the currently playing track."""
    if position_ms < 0:
        return "position_ms must be 0 or greater."
    try:
        await seek_to_position(position_ms)
    except (NotAuthenticatedError, SpotifyPlaybackError) as exc:
        return str(exc)
    return f"Seeked to {position_ms}ms."


@mcp_server.tool()
async def list_devices() -> str:
    """List the Spotify devices currently known to the user's account (phone,
    desktop app, web player, speakers, ...), including which one (if any) is
    active. Use this to see what's available before calling activate_device
    — the Spotify API can only control a device that's already open
    somewhere, it can't launch Spotify from nothing."""
    try:
        devices = await get_devices()
    except (NotAuthenticatedError, SpotifyAPIError) as exc:
        return str(exc)

    if not devices:
        return "No devices found. Open Spotify on a phone, desktop, or web player first."

    return "\n".join(
        f"{d['name']} ({d['type']}){' — active' if d['is_active'] else ''} — id: {d['id']}"
        for d in devices
    )


@mcp_server.tool()
async def activate_device(device_id: str, start_playing: bool = True) -> str:
    """Switch playback to a specific device (from list_devices) and
    optionally start playing on it."""
    try:
        await transfer_playback(device_id, play=start_playing)
    except (NotAuthenticatedError, SpotifyPlaybackError) as exc:
        return str(exc)
    return f"Switched playback to device {device_id}."
