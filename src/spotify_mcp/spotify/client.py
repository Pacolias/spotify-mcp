import asyncio
from typing import Any

import httpx

from spotify_mcp.spotify.auth import get_valid_access_token

SPOTIFY_API_BASE = "https://api.spotify.com/v1"

# Without an explicit timeout, a slow/hanging Spotify response would hang
# the calling MCP tool indefinitely instead of failing with a clear error.
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


async def _request(
    user_id: str,
    method: str,
    path: str,
    json: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> httpx.Response:
    token = await get_valid_access_token(user_id)
    async with httpx.AsyncClient(base_url=SPOTIFY_API_BASE, timeout=_TIMEOUT) as client:
        request = client.build_request(
            method, path, json=json, params=params, headers={"Authorization": f"Bearer {token}"}
        )
        response = await client.send(request)
        if response.status_code == 429:
            # Spotify's rate limit. Back off for as long as it tells us to,
            # then retry once, instead of surfacing a raw 429 to the caller.
            retry_after = float(response.headers.get("Retry-After", 1))
            await asyncio.sleep(retry_after)
            response = await client.send(request)
        return response


async def _get(user_id: str, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
    return await _request(user_id, "GET", path, params=params)


async def _post(
    user_id: str,
    path: str,
    json: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> httpx.Response:
    return await _request(user_id, "POST", path, json=json, params=params)


async def _put(
    user_id: str,
    path: str,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
) -> httpx.Response:
    return await _request(user_id, "PUT", path, params=params, json=json)


async def _delete(
    user_id: str,
    path: str,
    json: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> httpx.Response:
    return await _request(user_id, "DELETE", path, json=json, params=params)


async def search_tracks(user_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
    response = await _get(user_id, "/search", params={"q": query, "type": "track", "limit": limit})
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


async def search_playlists(user_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
    response = await _get(
        user_id, "/search", params={"q": query, "type": "playlist", "limit": limit}
    )
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


async def get_currently_playing(user_id: str) -> dict[str, Any] | None:
    response = await _get(user_id, "/me/player/currently-playing")
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


async def get_top_tracks(
    user_id: str, limit: int = 10, time_range: str = "medium_term"
) -> list[dict[str, Any]]:
    # time_range: short_term (~4 weeks), medium_term (~6 months), long_term (years).
    response = await _get(
        user_id, "/me/top/tracks", params={"limit": limit, "time_range": time_range}
    )
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


async def get_top_artists(
    user_id: str, limit: int = 10, time_range: str = "medium_term"
) -> list[dict[str, Any]]:
    response = await _get(
        user_id, "/me/top/artists", params={"limit": limit, "time_range": time_range}
    )
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


async def get_recently_played(user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    response = await _get(user_id, "/me/player/recently-played", params={"limit": limit})
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


async def list_playlists(user_id: str, limit: int = 20) -> list[dict[str, Any]]:
    response = await _get(user_id, "/me/playlists", params={"limit": limit})
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


async def get_playlist_tracks(
    user_id: str, playlist_id: str, limit: int = 50
) -> list[dict[str, Any]]:
    # The sub-resource endpoint is /items, not /tracks (which now 403s), and
    # each entry's track fields live directly under "item", not "item.track".
    # Both found by checking the real response, not assumed from docs.
    response = await _get(user_id, f"/playlists/{playlist_id}/items", params={"limit": limit})
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


async def create_playlist(
    user_id: str, name: str, description: str = "", public: bool = False
) -> dict[str, Any]:
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
        user_id,
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


async def add_tracks_to_playlist(user_id: str, playlist_id: str, track_ids: list[str]) -> None:
    # /playlists/{id}/tracks now 403s; /items is the working endpoint, same
    # rename pattern as get_playlist_tracks above.
    uris = [f"spotify:track:{track_id}" for track_id in track_ids]
    response = await _post(user_id, f"/playlists/{playlist_id}/items", json={"uris": uris})
    response.raise_for_status()


async def remove_tracks_from_playlist(user_id: str, playlist_id: str, track_ids: list[str]) -> None:
    # Found by trial against the real API, not documented: the DELETE body
    # shape doesn't match the POST /items shape. {"uris": [...]} (what adding
    # uses) 400s with "No uris provided"; the working shape is
    # {"items": [{"uri": "..."}, ...]}.
    items = [{"uri": f"spotify:track:{track_id}"} for track_id in track_ids]
    response = await _delete(user_id, f"/playlists/{playlist_id}/items", json={"items": items})
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


async def pause_playback(user_id: str) -> None:
    response = await _put(user_id, "/me/player/pause")
    _raise_for_playback_error(response)


async def resume_playback(user_id: str) -> None:
    response = await _put(user_id, "/me/player/play")
    _raise_for_playback_error(response)


async def skip_to_next(user_id: str) -> None:
    response = await _post(user_id, "/me/player/next")
    _raise_for_playback_error(response)


async def skip_to_previous(user_id: str) -> None:
    response = await _post(user_id, "/me/player/previous")
    _raise_for_playback_error(response)


async def set_volume(user_id: str, volume_percent: int) -> None:
    response = await _put(user_id, "/me/player/volume", params={"volume_percent": volume_percent})
    _raise_for_playback_error(response)


async def add_to_queue(user_id: str, track_id: str) -> None:
    response = await _post(user_id, "/me/player/queue", params={"uri": f"spotify:track:{track_id}"})
    _raise_for_playback_error(response)


async def set_shuffle(user_id: str, enabled: bool) -> None:
    response = await _put(
        user_id, "/me/player/shuffle", params={"state": "true" if enabled else "false"}
    )
    _raise_for_playback_error(response)


async def set_repeat_mode(user_id: str, mode: str) -> None:
    # mode: "track", "context" (repeat the playlist/album), or "off".
    response = await _put(user_id, "/me/player/repeat", params={"state": mode})
    _raise_for_playback_error(response)


async def seek_to_position(user_id: str, position_ms: int) -> None:
    response = await _put(user_id, "/me/player/seek", params={"position_ms": position_ms})
    _raise_for_playback_error(response)


async def get_saved_tracks(user_id: str, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    # Spotify caps limit at 50 per call; page through with offset for more.
    response = await _get(user_id, "/me/tracks", params={"limit": limit, "offset": offset})
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


async def save_tracks(user_id: str, track_ids: list[str]) -> None:
    response = await _put(user_id, "/me/tracks", params={"ids": ",".join(track_ids)})
    _raise_for_api_error(response)


async def remove_saved_tracks(user_id: str, track_ids: list[str]) -> None:
    response = await _delete(user_id, "/me/tracks", params={"ids": ",".join(track_ids)})
    _raise_for_api_error(response)


async def get_devices(user_id: str) -> list[dict[str, Any]]:
    response = await _get(user_id, "/me/player/devices")
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


async def transfer_playback(user_id: str, device_id: str, play: bool = True) -> None:
    response = await _put(user_id, "/me/player", json={"device_ids": [device_id], "play": play})
    _raise_for_playback_error(response)


async def get_current_user_profile(user_id: str) -> dict[str, Any]:
    response = await _get(user_id, "/me")
    response.raise_for_status()
    payload = response.json()
    return {
        "id": payload["id"],
        "display_name": payload.get("display_name"),
        "followers": payload["followers"]["total"],
        "url": payload["external_urls"]["spotify"],
        "image_url": payload["images"][0]["url"] if payload.get("images") else None,
    }
