import httpx
import respx

from spotify_mcp.mcp.tools.playlists import playlist_tracks
from spotify_mcp.mcp.tools.search import search_track
from spotify_mcp.spotify.client import SPOTIFY_API_BASE


@respx.mock
async def test_playlist_tracks_output_includes_track_ids(logged_in) -> None:
    # Regression test: an earlier version formatted only name/artists and
    # silently dropped the track id, which made it impossible to feed the
    # result into add_tracks / remove_tracks_from_playlist — those need ids.
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

    output = await playlist_tracks("p1")

    assert "id: t1" in output


@respx.mock
async def test_search_track_output_includes_track_ids(logged_in) -> None:
    respx.get(f"{SPOTIFY_API_BASE}/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "tracks": {
                    "items": [
                        {
                            "id": "t1",
                            "name": "Track One",
                            "artists": [{"name": "Artist A"}],
                            "album": {"name": "Album A"},
                            "external_urls": {"spotify": "https://open.spotify.com/track/t1"},
                        }
                    ]
                }
            },
        )
    )

    output = await search_track("Track One")

    assert "id: t1" in output
