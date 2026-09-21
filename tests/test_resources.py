import httpx
import respx

from spotify_mcp.mcp.resources import (
    now_playing_resource,
    playlist_resource,
    playlists_resource,
)
from spotify_mcp.spotify.client import SPOTIFY_API_BASE


@respx.mock
async def test_now_playing_resource_returns_track(logged_in) -> None:
    respx.get(f"{SPOTIFY_API_BASE}/me/player/currently-playing").mock(
        return_value=httpx.Response(
            200,
            json={
                "is_playing": True,
                "progress_ms": 1000,
                "item": {
                    "name": "Track",
                    "artists": [{"name": "Artist"}],
                    "album": {"name": "Album"},
                    "duration_ms": 2000,
                    "external_urls": {"spotify": "https://open.spotify.com/track/t1"},
                },
            },
        )
    )

    result = await now_playing_resource()

    assert result["name"] == "Track"
    assert result["is_playing"] is True


@respx.mock
async def test_now_playing_resource_handles_nothing_playing(logged_in) -> None:
    respx.get(f"{SPOTIFY_API_BASE}/me/player/currently-playing").mock(
        return_value=httpx.Response(204)
    )

    result = await now_playing_resource()

    assert result == {"is_playing": False}


@respx.mock
async def test_playlists_resource_returns_playlists(logged_in) -> None:
    respx.get(f"{SPOTIFY_API_BASE}/me/playlists").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "p1",
                        "name": "Playlist",
                        "items": {"total": 1},
                        "public": True,
                        "external_urls": {"spotify": "https://open.spotify.com/playlist/p1"},
                    }
                ]
            },
        )
    )

    result = await playlists_resource()

    assert result["playlists"][0]["id"] == "p1"


@respx.mock
async def test_playlist_resource_returns_tracks_for_given_id(logged_in) -> None:
    respx.get(f"{SPOTIFY_API_BASE}/playlists/p1/items").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "item": {
                            "id": "t1",
                            "name": "Track",
                            "artists": [{"name": "Artist"}],
                            "external_urls": {"spotify": "https://open.spotify.com/track/t1"},
                        }
                    }
                ]
            },
        )
    )

    result = await playlist_resource("p1")

    assert result["playlist_id"] == "p1"
    assert result["tracks"][0]["id"] == "t1"
