import httpx
import respx

from spotify_mcp.mcp.resources import dashboard_resource, profile_resource
from spotify_mcp.spotify.client import SPOTIFY_API_BASE


@respx.mock
async def test_profile_resource_parses_user(logged_in) -> None:
    respx.get(f"{SPOTIFY_API_BASE}/me").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "user1",
                "display_name": "Test User",
                "followers": {"total": 5},
                "external_urls": {"spotify": "https://open.spotify.com/user/user1"},
                "images": [{"url": "https://example.com/pic.jpg"}],
            },
        )
    )

    result = await profile_resource()

    assert result == {
        "id": "user1",
        "display_name": "Test User",
        "followers": 5,
        "url": "https://open.spotify.com/user/user1",
        "image_url": "https://example.com/pic.jpg",
    }


@respx.mock
async def test_profile_resource_handles_no_images(logged_in) -> None:
    respx.get(f"{SPOTIFY_API_BASE}/me").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "user1",
                "display_name": "Test User",
                "followers": {"total": 0},
                "external_urls": {"spotify": "https://open.spotify.com/user/user1"},
                "images": [],
            },
        )
    )

    result = await profile_resource()

    assert result["image_url"] is None


@respx.mock
async def test_dashboard_resource_combines_all_sections(logged_in) -> None:
    respx.get(f"{SPOTIFY_API_BASE}/me/player/currently-playing").mock(
        return_value=httpx.Response(204)
    )
    respx.get(f"{SPOTIFY_API_BASE}/me/player/devices").mock(
        return_value=httpx.Response(200, json={"devices": []})
    )
    respx.get(f"{SPOTIFY_API_BASE}/me/top/tracks").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    respx.get(f"{SPOTIFY_API_BASE}/me/player/recently-played").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    result = await dashboard_resource()

    assert result == {
        "now_playing": {"is_playing": False},
        "devices": [],
        "top_tracks": [],
        "recently_played": [],
    }


@respx.mock
async def test_dashboard_resource_tolerates_a_failing_section(logged_in) -> None:
    # devices fails, but the rest of the dashboard should still come back —
    # one section failing shouldn't blank out the whole snapshot.
    respx.get(f"{SPOTIFY_API_BASE}/me/player/currently-playing").mock(
        return_value=httpx.Response(204)
    )
    respx.get(f"{SPOTIFY_API_BASE}/me/player/devices").mock(
        return_value=httpx.Response(403, json={"error": {"message": "Forbidden"}})
    )
    respx.get(f"{SPOTIFY_API_BASE}/me/top/tracks").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    respx.get(f"{SPOTIFY_API_BASE}/me/player/recently-played").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    result = await dashboard_resource()

    assert result["devices"] is None
    assert result["top_tracks"] == []
