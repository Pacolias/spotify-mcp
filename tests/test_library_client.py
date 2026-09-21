import httpx
import pytest
import respx

from spotify_mcp.mcp.tools.library import like_tracks
from spotify_mcp.spotify.client import (
    SPOTIFY_API_BASE,
    SpotifyAPIError,
    get_saved_tracks,
    remove_saved_tracks,
    save_tracks,
)


@respx.mock
async def test_get_saved_tracks_parses_results(logged_in) -> None:
    respx.get(f"{SPOTIFY_API_BASE}/me/tracks").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "track": {
                            "id": "t1",
                            "name": "Track One",
                            "artists": [{"name": "Artist A"}],
                            "album": {"name": "Album A"},
                            "external_urls": {"spotify": "https://open.spotify.com/track/t1"},
                        }
                    }
                ]
            },
        )
    )

    results = await get_saved_tracks(limit=1)

    assert results == [
        {
            "id": "t1",
            "name": "Track One",
            "artists": ["Artist A"],
            "album": "Album A",
            "url": "https://open.spotify.com/track/t1",
        }
    ]


@respx.mock
async def test_get_saved_tracks_sends_offset_param(logged_in) -> None:
    # Spotify caps limit at 50 (confirmed against the real API — see
    # journal); offset is how a large Liked Songs library gets paged
    # through.
    route = respx.get(f"{SPOTIFY_API_BASE}/me/tracks").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    await get_saved_tracks(limit=10, offset=20)

    assert route.calls.last.request.url.params["offset"] == "20"


@respx.mock
async def test_save_tracks_raises_spotify_api_error_with_message(logged_in) -> None:
    # Found by testing against a real account: PUT /me/tracks returns a
    # bare 403 "Forbidden" — Spotify restricts modifying Liked Songs to
    # apps with "Extended Quota Mode" approval, distinct from a scope
    # error (reading /me/tracks works fine with the same token).
    respx.put(f"{SPOTIFY_API_BASE}/me/tracks").mock(
        return_value=httpx.Response(403, json={"error": {"status": 403, "message": "Forbidden"}})
    )

    with pytest.raises(SpotifyAPIError, match="Forbidden"):
        await save_tracks(["t1"])


@respx.mock
async def test_remove_saved_tracks_raises_spotify_api_error_with_message(logged_in) -> None:
    respx.delete(f"{SPOTIFY_API_BASE}/me/tracks").mock(
        return_value=httpx.Response(403, json={"error": {"status": 403, "message": "Forbidden"}})
    )

    with pytest.raises(SpotifyAPIError, match="Forbidden"):
        await remove_saved_tracks(["t1"])


@respx.mock
async def test_like_tracks_tool_returns_friendly_message_instead_of_raising(logged_in) -> None:
    respx.put(f"{SPOTIFY_API_BASE}/me/tracks").mock(
        return_value=httpx.Response(403, json={"error": {"status": 403, "message": "Forbidden"}})
    )

    result = await like_tracks(["t1"])

    assert result == "Spotify API error: Forbidden"
