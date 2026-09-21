import httpx
import respx

from spotify_mcp.spotify.client import SPOTIFY_API_BASE, get_currently_playing, search_tracks


@respx.mock
async def test_search_tracks_parses_results(logged_in) -> None:
    respx.get(f"{SPOTIFY_API_BASE}/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "tracks": {
                    "items": [
                        {
                            "id": "abc123",
                            "name": "Bohemian Rhapsody",
                            "artists": [{"name": "Queen"}],
                            "album": {"name": "A Night at the Opera"},
                            "external_urls": {"spotify": "https://open.spotify.com/track/abc123"},
                        }
                    ]
                }
            },
        )
    )

    results = await search_tracks("Bohemian Rhapsody")

    assert results == [
        {
            "id": "abc123",
            "name": "Bohemian Rhapsody",
            "artists": ["Queen"],
            "album": "A Night at the Opera",
            "url": "https://open.spotify.com/track/abc123",
        }
    ]


@respx.mock
async def test_currently_playing_returns_none_when_nothing_playing(logged_in) -> None:
    respx.get(f"{SPOTIFY_API_BASE}/me/player/currently-playing").mock(
        return_value=httpx.Response(204)
    )

    assert await get_currently_playing() is None


@respx.mock
async def test_currently_playing_parses_active_playback(logged_in) -> None:
    respx.get(f"{SPOTIFY_API_BASE}/me/player/currently-playing").mock(
        return_value=httpx.Response(
            200,
            json={
                "is_playing": True,
                "progress_ms": 1000,
                "item": {
                    "name": "Track name",
                    "artists": [{"name": "Artist"}],
                    "album": {"name": "Album"},
                    "duration_ms": 200000,
                    "external_urls": {"spotify": "https://open.spotify.com/track/xyz"},
                },
            },
        )
    )

    result = await get_currently_playing()

    assert result == {
        "name": "Track name",
        "artists": ["Artist"],
        "album": "Album",
        "is_playing": True,
        "progress_ms": 1000,
        "duration_ms": 200000,
        "url": "https://open.spotify.com/track/xyz",
    }
