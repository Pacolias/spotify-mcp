from spotify_mcp.mcp.server import mcp_server
from spotify_mcp.spotify.auth import NotAuthenticatedError
from spotify_mcp.spotify.client import search_tracks


@mcp_server.tool()
async def search_track(query: str, limit: int = 5) -> str:
    """Search Spotify's catalog for tracks matching a query (song name, artist, etc.)."""
    try:
        results = await search_tracks(query, limit=limit)
    except NotAuthenticatedError as exc:
        return str(exc)

    if not results:
        return f"No tracks found for '{query}'."

    return "\n".join(
        f"{r['name']} — {', '.join(r['artists'])} ({r['album']}): {r['url']}" for r in results
    )
