import json

import httpx
import respx

from spotify_mcp.spotify.client import (
    SPOTIFY_API_BASE,
    add_tracks_to_playlist,
    create_playlist,
    get_playlist_tracks,
    list_playlists,
)


@respx.mock
async def test_list_playlists_parses_results(logged_in) -> None:
    respx.get(f"{SPOTIFY_API_BASE}/me/playlists").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "p1",
                        "name": "Playlist One",
                        "items": {"total": 5},
                        "public": False,
                        "external_urls": {"spotify": "https://open.spotify.com/playlist/p1"},
                    }
                ]
            },
        )
    )

    results = await list_playlists(limit=1)

    assert results == [
        {
            "id": "p1",
            "name": "Playlist One",
            "track_count": 5,
            "public": False,
            "url": "https://open.spotify.com/playlist/p1",
        }
    ]


@respx.mock
async def test_get_playlist_tracks_parses_results(logged_in) -> None:
    # Note the real endpoint is /items (not /tracks, which 403s — see
    # journal entry 15), and each entry's track fields live directly under
    # "item", not "item.track".
    respx.get(f"{SPOTIFY_API_BASE}/playlists/p1/items").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "item": {
                            "id": "t1",
                            "name": "Track One",
                            "artists": [{"name": "Artist A"}],
                            "external_urls": {"spotify": "https://open.spotify.com/track/t1"},
                        }
                    }
                ]
            },
        )
    )

    results = await get_playlist_tracks("p1")

    assert results == [
        {
            "id": "t1",
            "name": "Track One",
            "artists": ["Artist A"],
            "url": "https://open.spotify.com/track/t1",
        }
    ]


@respx.mock
async def test_create_playlist_posts_to_me_playlists(logged_in) -> None:
    # The documented POST /users/{user_id}/playlists 403s; POST /me/playlists
    # is what actually works (see journal entry 15).
    route = respx.post(f"{SPOTIFY_API_BASE}/me/playlists").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "new-playlist",
                "name": "My Playlist",
                "external_urls": {"spotify": "https://open.spotify.com/playlist/new-playlist"},
            },
        )
    )

    result = await create_playlist("My Playlist", description="desc", public=False)

    assert result == {
        "id": "new-playlist",
        "name": "My Playlist",
        "url": "https://open.spotify.com/playlist/new-playlist",
    }
    assert json.loads(route.calls.last.request.content) == {
        "name": "My Playlist",
        "description": "desc",
        "public": False,
    }


@respx.mock
async def test_add_tracks_to_playlist_posts_to_items(logged_in) -> None:
    route = respx.post(f"{SPOTIFY_API_BASE}/playlists/p1/items").mock(
        return_value=httpx.Response(201, json={"snapshot_id": "abc"})
    )

    await add_tracks_to_playlist("p1", ["t1", "t2"])

    assert json.loads(route.calls.last.request.content) == {
        "uris": ["spotify:track:t1", "spotify:track:t2"]
    }
