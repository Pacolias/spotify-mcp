from spotify_mcp.mcp.server import mcp_server
from spotify_mcp.spotify.auth import NotAuthenticatedError
from spotify_mcp.spotify.client import get_currently_playing


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
