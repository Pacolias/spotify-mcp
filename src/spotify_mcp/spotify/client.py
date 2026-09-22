import httpx

from spotify_mcp.spotify.auth import get_valid_access_token

SPOTIFY_API_BASE = "https://api.spotify.com/v1"


async def _get(path: str, params: dict | None = None) -> httpx.Response:
    token = await get_valid_access_token()
    async with httpx.AsyncClient(base_url=SPOTIFY_API_BASE) as client:
        return await client.get(path, params=params, headers={"Authorization": f"Bearer {token}"})


async def _post(
    path: str, json: dict | None = None, params: dict | None = None
) -> httpx.Response:
    token = await get_valid_access_token()
    async with httpx.AsyncClient(base_url=SPOTIFY_API_BASE) as client:
        return await client.post(
            path, json=json, params=params, headers={"Authorization": f"Bearer {token}"}
        )


async def _put(
    path: str, params: dict | None = None, json: dict | None = None
) -> httpx.Response:
    token = await get_valid_access_token()
    async with httpx.AsyncClient(base_url=SPOTIFY_API_BASE) as client:
        return await client.put(
            path, params=params, json=json, headers={"Authorization": f"Bearer {token}"}
        )


async def _delete(
    path: str, json: dict | None = None, params: dict | None = None
) -> httpx.Response:
    token = await get_valid_access_token()
    async with httpx.AsyncClient(base_url=SPOTIFY_API_BASE) as client:
        request = client.build_request(
            "DELETE", path, json=json, params=params, headers={"Authorization": f"Bearer {token}"}
        )
        return await client.send(request)


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


async def search_playlists(query: str, limit: int = 5) -> list[dict]:
    response = await _get("/search", params={"q": query, "type": "playlist", "limit": limit})
    response.raise_for_status()
    items = response.json()["playlists"]["items"]
    return [
        {
            "id": item["id"],
            "name": item["name"],
            "owner": item["owner"]["display_name"],
            "description": item.get("description") or "",
            "url": item["external_urls"]["spotify"],
        }
        for item in items
        if item  # Spotify's playlist search sometimes includes null entries
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


async def list_playlists(limit: int = 20) -> list[dict]:
    response = await _get("/me/playlists", params={"limit": limit})
    response.raise_for_status()
    items = response.json()["items"]
    return [
        {
            "id": item["id"],
            "name": item["name"],
            # Spotify's playlist object nests this under "items", not the
            # "tracks" key the older docs describe — found by checking the
            # real response, not assumed.
            "track_count": item["items"]["total"],
            "public": item["public"],
            "url": item["external_urls"]["spotify"],
        }
        for item in items
    ]


async def get_playlist_tracks(playlist_id: str, limit: int = 50) -> list[dict]:
    # The sub-resource endpoint is /items, not /tracks (which now 403s), and
    # each entry's track fields live directly under "item", not "item.track".
    # Both found by checking the real response, not assumed from docs.
    response = await _get(f"/playlists/{playlist_id}/items", params={"limit": limit})
    response.raise_for_status()
    items = response.json()["items"]
    return [
        {
            "id": entry["item"]["id"],
            "name": entry["item"]["name"],
            "artists": [artist["name"] for artist in entry["item"]["artists"]],
            "url": entry["item"]["external_urls"]["spotify"],
        }
        for entry in items
        if entry.get("item")
    ]


async def create_playlist(name: str, description: str = "", public: bool = False) -> dict:
    # The documented POST /users/{user_id}/playlists now 403s; POST /me/playlists
    # works instead (and skips having to look up the user id first). Found by
    # checking the real API, not assumed from docs.
    #
    # `public: False` is sent correctly below but Spotify ignores it and
    # creates the playlist public anyway — confirmed against the real API
    # with the full scope already granted, and matches widely reported
    # community bug threads. Not fixable client-side (a follow-up PUT to
    # change-playlist-details doesn't honor it either); see journal entry 30.
    response = await _post(
        "/me/playlists",
        json={"name": name, "description": description, "public": public},
    )
    response.raise_for_status()
    payload = response.json()
    return {
        "id": payload["id"],
        "name": payload["name"],
        "url": payload["external_urls"]["spotify"],
    }


async def add_tracks_to_playlist(playlist_id: str, track_ids: list[str]) -> None:
    # /playlists/{id}/tracks now 403s; /items is the working endpoint, same
    # rename pattern as get_playlist_tracks above.
    uris = [f"spotify:track:{track_id}" for track_id in track_ids]
    response = await _post(f"/playlists/{playlist_id}/items", json={"uris": uris})
    response.raise_for_status()


async def remove_tracks_from_playlist(playlist_id: str, track_ids: list[str]) -> None:
    # Found by trial against the real API, not documented: the DELETE body
    # shape doesn't match the POST /items shape. {"uris": [...]} (what adding
    # uses) 400s with "No uris provided"; the working shape is
    # {"items": [{"uri": "..."}, ...]}.
    items = [{"uri": f"spotify:track:{track_id}"} for track_id in track_ids]
    response = await _delete(f"/playlists/{playlist_id}/items", json={"items": items})
    response.raise_for_status()


class SpotifyPlaybackError(Exception):
    """Raised for a failed playback-control call, with Spotify's own error
    message (e.g. "Player command failed: No active device found") instead
    of a raw HTTP status — playback endpoints commonly fail for reasons the
    caller should see verbatim (no active device, restricted action, ...)."""


def _raise_for_playback_error(response: httpx.Response) -> None:
    if response.is_success:
        return
    try:
        message = response.json()["error"]["message"]
    except Exception:
        message = response.text or f"HTTP {response.status_code}"
    raise SpotifyPlaybackError(message)


async def pause_playback() -> None:
    response = await _put("/me/player/pause")
    _raise_for_playback_error(response)


async def resume_playback() -> None:
    response = await _put("/me/player/play")
    _raise_for_playback_error(response)


async def skip_to_next() -> None:
    response = await _post("/me/player/next")
    _raise_for_playback_error(response)


async def skip_to_previous() -> None:
    response = await _post("/me/player/previous")
    _raise_for_playback_error(response)


async def set_volume(volume_percent: int) -> None:
    response = await _put("/me/player/volume", params={"volume_percent": volume_percent})
    _raise_for_playback_error(response)


async def add_to_queue(track_id: str) -> None:
    response = await _post("/me/player/queue", params={"uri": f"spotify:track:{track_id}"})
    _raise_for_playback_error(response)


async def set_shuffle(enabled: bool) -> None:
    response = await _put(
        "/me/player/shuffle", params={"state": "true" if enabled else "false"}
    )
    _raise_for_playback_error(response)


async def set_repeat_mode(mode: str) -> None:
    # mode: "track", "context" (repeat the playlist/album), or "off".
    response = await _put("/me/player/repeat", params={"state": mode})
    _raise_for_playback_error(response)


async def seek_to_position(position_ms: int) -> None:
    response = await _put("/me/player/seek", params={"position_ms": position_ms})
    _raise_for_playback_error(response)


async def get_saved_tracks(limit: int = 20, offset: int = 0) -> list[dict]:
    # Spotify caps limit at 50 per call; page through with offset for more.
    response = await _get("/me/tracks", params={"limit": limit, "offset": offset})
    response.raise_for_status()
    items = response.json()["items"]
    return [
        {
            "id": entry["track"]["id"],
            "name": entry["track"]["name"],
            "artists": [artist["name"] for artist in entry["track"]["artists"]],
            "album": entry["track"]["album"]["name"],
            "url": entry["track"]["external_urls"]["spotify"],
        }
        for entry in items
    ]


class SpotifyAPIError(Exception):
    """Raised for a failed write call, with Spotify's own error message
    instead of a raw HTTP status. Some write endpoints — like this one, see
    save_tracks below — return a bare 403 "Forbidden" for apps without
    Spotify's "Extended Quota Mode" approval, distinct from a scope error;
    that message is worth surfacing verbatim rather than a stacktrace."""


def _raise_for_api_error(response: httpx.Response) -> None:
    if response.is_success:
        return
    try:
        message = response.json()["error"]["message"]
    except Exception:
        message = response.text or f"HTTP {response.status_code}"
    raise SpotifyAPIError(message)


async def save_tracks(track_ids: list[str]) -> None:
    response = await _put("/me/tracks", params={"ids": ",".join(track_ids)})
    _raise_for_api_error(response)


async def remove_saved_tracks(track_ids: list[str]) -> None:
    response = await _delete("/me/tracks", params={"ids": ",".join(track_ids)})
    _raise_for_api_error(response)


async def get_devices() -> list[dict]:
    response = await _get("/me/player/devices")
    _raise_for_api_error(response)
    return [
        {
            "id": d["id"],
            "name": d["name"],
            "type": d["type"],
            "is_active": d["is_active"],
            "volume_percent": d.get("volume_percent"),
        }
        for d in response.json()["devices"]
    ]


async def transfer_playback(device_id: str, play: bool = True) -> None:
    response = await _put("/me/player", json={"device_ids": [device_id], "play": play})
    _raise_for_playback_error(response)


async def get_current_user_profile() -> dict:
    response = await _get("/me")
    response.raise_for_status()
    payload = response.json()
    return {
        "id": payload["id"],
        "display_name": payload.get("display_name"),
        "followers": payload["followers"]["total"],
        "url": payload["external_urls"]["spotify"],
        "image_url": payload["images"][0]["url"] if payload.get("images") else None,
    }
