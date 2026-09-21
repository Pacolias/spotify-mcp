from spotify_mcp.mcp.server import mcp_server
from spotify_mcp.spotify.auth import NotAuthenticatedError
from spotify_mcp.spotify.client import get_recently_played, get_top_artists, get_top_tracks

@mcp_server.tool()
async def top_tracks(limit: int = 10, time_range: str = "medium_term") -> str:
    """Get the user's most-listened-to tracks. time_range: short_term
    (~4 weeks), medium_term (~6 months, default), or long_term (years)."""
    try:
        results = await get_top_tracks(limit=limit, time_range=time_range)
    except NotAuthenticatedError as exc:
        return str(exc)

    if not results:
        return "No top tracks available for this time range."

    return "\n".join(f"{t['name']} — {', '.join(t['artists'])} ({t['album']})" for t in results)


@mcp_server.tool()
async def top_artists(limit: int = 10, time_range: str = "medium_term") -> str:
    """Get the user's most-listened-to artists. time_range: short_term
    (~4 weeks), medium_term (~6 months, default), or long_term (years)."""
    try:
        results = await get_top_artists(limit=limit, time_range=time_range)
    except NotAuthenticatedError as exc:
        return str(exc)

    if not results:
        return "No top artists available for this time range."

    return "\n".join(
        f"{a['name']}" + (f" ({', '.join(a['genres'])})" if a["genres"] else "")
        for a in results
    )


@mcp_server.tool()
async def recently_played(limit: int = 10) -> str:
    """Get the user's most recently played tracks, most recent first."""
    try:
        results = await get_recently_played(limit=limit)
    except NotAuthenticatedError as exc:
        return str(exc)

    if not results:
        return "No recent playback history."

    return "\n".join(
        f"{r['played_at']} — {r['name']} — {', '.join(r['artists'])}" for r in results
    )
