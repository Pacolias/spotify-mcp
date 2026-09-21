import httpx
import respx

from spotify_mcp.spotify.client import (
    SPOTIFY_API_BASE,
    get_recently_played,
    get_top_artists,
    get_top_tracks,
)


@respx.mock
async def test_get_top_tracks_parses_results(logged_in) -> None:
    respx.get(f"{SPOTIFY_API_BASE}/me/top/tracks").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "t1",
                        "name": "Track One",
                        "artists": [{"name": "Artist A"}],
                        "album": {"name": "Album A"},
                        "external_urls": {"spotify": "https://open.spotify.com/track/t1"},
                    }
                ]
            },
        )
    )

    results = await get_top_tracks(limit=1)

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
async def test_get_top_artists_parses_results(logged_in) -> None:
    respx.get(f"{SPOTIFY_API_BASE}/me/top/artists").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "a1",
                        "name": "Artist A",
                        "genres": ["pop"],
                        "external_urls": {"spotify": "https://open.spotify.com/artist/a1"},
                    }
                ]
            },
        )
    )

    results = await get_top_artists(limit=1)

    assert results == [
        {
            "id": "a1",
            "name": "Artist A",
            "genres": ["pop"],
            "url": "https://open.spotify.com/artist/a1",
        }
    ]


@respx.mock
async def test_get_recently_played_parses_results(logged_in) -> None:
    respx.get(f"{SPOTIFY_API_BASE}/me/player/recently-played").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "played_at": "2026-09-21T18:00:00.000Z",
                        "track": {
                            "name": "Track One",
                            "artists": [{"name": "Artist A"}],
                            "album": {"name": "Album A"},
                            "external_urls": {"spotify": "https://open.spotify.com/track/t1"},
                        },
                    }
                ]
            },
        )
    )

    results = await get_recently_played(limit=1)

    assert results == [
        {
            "name": "Track One",
            "artists": ["Artist A"],
            "album": "Album A",
            "played_at": "2026-09-21T18:00:00.000Z",
            "url": "https://open.spotify.com/track/t1",
        }
    ]
