import httpx

from spotify_mcp.spotify.auth import get_valid_access_token

SPOTIFY_API_BASE = "https://api.spotify.com/v1"


async def _get(path: str, params: dict | None = None) -> httpx.Response:
    token = await get_valid_access_token()
    async with httpx.AsyncClient(base_url=SPOTIFY_API_BASE) as client:
        return await client.get(path, params=params, headers={"Authorization": f"Bearer {token}"})


async def search_tracks(query: str, limit: int = 5) -> list[dict]:
    response = await _get("/search", params={"q": query, "type": "track", "limit": limit})
    response.raise_for_status()
    items = response.json()["tracks"]["items"]
    return [
        {
            "id": item["id"],
            "name": item["name"],
            "artists": [artist["name"] for artist in item["artists"]],
            "album": item["album"]["name"],
            "url": item["external_urls"]["spotify"],
        }
        for item in items
    ]


async def get_currently_playing() -> dict | None:
    response = await _get("/me/player/currently-playing")
    if response.status_code == 204:
        # Spotify's documented way of saying "nothing is playing right now".
        return None
    response.raise_for_status()

    payload = response.json()
    item = payload.get("item")
    if item is None:
        return None

    return {
        "name": item["name"],
        "artists": [artist["name"] for artist in item["artists"]],
        "album": item["album"]["name"],
        "is_playing": payload["is_playing"],
        "progress_ms": payload.get("progress_ms"),
        "duration_ms": item.get("duration_ms"),
        "url": item["external_urls"]["spotify"],
    }


async def get_top_tracks(limit: int = 10, time_range: str = "medium_term") -> list[dict]:
    # time_range: short_term (~4 weeks), medium_term (~6 months), long_term (years).
    response = await _get("/me/top/tracks", params={"limit": limit, "time_range": time_range})
    response.raise_for_status()
    items = response.json()["items"]
    return [
        {
            "id": item["id"],
            "name": item["name"],
            "artists": [artist["name"] for artist in item["artists"]],
            "album": item["album"]["name"],
            "url": item["external_urls"]["spotify"],
        }
        for item in items
    ]


async def get_top_artists(limit: int = 10, time_range: str = "medium_term") -> list[dict]:
    response = await _get("/me/top/artists", params={"limit": limit, "time_range": time_range})
    response.raise_for_status()
    items = response.json()["items"]
    return [
        {
            "id": item["id"],
            "name": item["name"],
            "genres": item.get("genres", []),
            "url": item["external_urls"]["spotify"],
        }
        for item in items
    ]


async def get_recently_played(limit: int = 10) -> list[dict]:
    response = await _get("/me/player/recently-played", params={"limit": limit})
    response.raise_for_status()
    items = response.json()["items"]
    return [
        {
            "name": entry["track"]["name"],
            "artists": [artist["name"] for artist in entry["track"]["artists"]],
            "album": entry["track"]["album"]["name"],
            "played_at": entry["played_at"],
            "url": entry["track"]["external_urls"]["spotify"],
        }
        for entry in items
    ]
