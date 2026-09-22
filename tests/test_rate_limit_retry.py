import httpx
import respx

import spotify_mcp.spotify.client as client_module
from spotify_mcp.spotify.client import SPOTIFY_API_BASE, search_tracks


@respx.mock
async def test_429_is_retried_once_after_the_retry_after_delay(logged_in, monkeypatch) -> None:
    slept_for = []

    async def fake_sleep(seconds: float) -> None:
        slept_for.append(seconds)

    monkeypatch.setattr(client_module.asyncio, "sleep", fake_sleep)

    route = respx.get(f"{SPOTIFY_API_BASE}/search").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "2"}),
            httpx.Response(200, json={"tracks": {"items": []}}),
        ]
    )

    results = await search_tracks("anything")

    assert results == []
    assert route.call_count == 2
    assert slept_for == [2.0]
