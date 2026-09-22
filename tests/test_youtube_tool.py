import httpx
import respx

from spotify_mcp.mcp.tools import youtube as youtube_tool
from spotify_mcp.spotify.client import SPOTIFY_API_BASE


@respx.mock
async def test_import_youtube_playlist_skips_artist_mismatches(monkeypatch, logged_in) -> None:
    # Reproduces a real scenario hit while testing against a live video:
    # a real track ("Real Song" by 1aevne) alongside an "unreleased" one
    # that isn't on Spotify at all — its search still returns *something*,
    # just by an unrelated artist, and that has to be rejected rather than
    # silently added to the playlist.
    monkeypatch.setattr(
        youtube_tool,
        "extract_tracklist",
        lambda url: ["1aevne - Real Song", "1aevne - unreleased track"],
    )

    call_count = {"n": 0}

    def search_response(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        if call_count["n"] == 1:
            item = {
                "id": "t1",
                "name": "Real Song",
                "artists": [{"name": "1aevne"}],
                "album": {"name": "Album"},
                "external_urls": {"spotify": "https://open.spotify.com/track/t1"},
            }
        else:
            item = {
                "id": "wrong",
                "name": "Wrong Song",
                "artists": [{"name": "Unrelated Artist"}],
                "album": {"name": "Album"},
                "external_urls": {"spotify": "https://open.spotify.com/track/wrong"},
            }
        return httpx.Response(200, json={"tracks": {"items": [item]}})

    respx.get(f"{SPOTIFY_API_BASE}/search").mock(side_effect=search_response)
    respx.post(f"{SPOTIFY_API_BASE}/me/playlists").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "p1",
                "name": "My Playlist",
                "external_urls": {"spotify": "https://open.spotify.com/playlist/p1"},
            },
        )
    )
    add_route = respx.post(f"{SPOTIFY_API_BASE}/playlists/p1/items").mock(
        return_value=httpx.Response(201, json={"snapshot_id": "abc"})
    )

    result = await youtube_tool.import_youtube_playlist(
        "https://youtube.com/watch?v=x", "My Playlist"
    )

    assert "1/2" in result
    assert "Real Song — 1aevne" in result
    assert "No confident Spotify match:" in result
    assert "1aevne - unreleased track" in result
    assert "Wrong Song" not in result

    import json

    assert json.loads(add_route.calls.last.request.content) == {"uris": ["spotify:track:t1"]}
