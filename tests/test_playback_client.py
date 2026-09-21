import httpx
import pytest
import respx

from spotify_mcp.spotify.client import (
    SPOTIFY_API_BASE,
    add_to_queue,
    pause_playback,
    resume_playback,
    set_volume,
    skip_to_next,
    skip_to_previous,
)


@respx.mock
async def test_pause_playback_calls_pause_endpoint(logged_in) -> None:
    route = respx.put(f"{SPOTIFY_API_BASE}/me/player/pause").mock(
        return_value=httpx.Response(200, text="snapshot-id")
    )

    await pause_playback()

    assert route.called


@respx.mock
async def test_resume_playback_calls_play_endpoint(logged_in) -> None:
    route = respx.put(f"{SPOTIFY_API_BASE}/me/player/play").mock(
        return_value=httpx.Response(200, text="snapshot-id")
    )

    await resume_playback()

    assert route.called


@respx.mock
async def test_skip_to_next_calls_next_endpoint(logged_in) -> None:
    route = respx.post(f"{SPOTIFY_API_BASE}/me/player/next").mock(
        return_value=httpx.Response(200, text="snapshot-id")
    )

    await skip_to_next()

    assert route.called


@respx.mock
async def test_skip_to_previous_calls_previous_endpoint(logged_in) -> None:
    route = respx.post(f"{SPOTIFY_API_BASE}/me/player/previous").mock(
        return_value=httpx.Response(200, text="snapshot-id")
    )

    await skip_to_previous()

    assert route.called


@respx.mock
async def test_set_volume_sends_volume_percent_param(logged_in) -> None:
    route = respx.put(f"{SPOTIFY_API_BASE}/me/player/volume").mock(return_value=httpx.Response(204))

    await set_volume(55)

    assert route.calls.last.request.url.params["volume_percent"] == "55"


@respx.mock
async def test_add_to_queue_sends_track_uri_param(logged_in) -> None:
    route = respx.post(f"{SPOTIFY_API_BASE}/me/player/queue").mock(
        return_value=httpx.Response(200, text="snapshot-id")
    )

    await add_to_queue("abc123")

    assert route.calls.last.request.url.params["uri"] == "spotify:track:abc123"


@respx.mock
async def test_pause_playback_raises_on_error(logged_in) -> None:
    respx.put(f"{SPOTIFY_API_BASE}/me/player/pause").mock(
        return_value=httpx.Response(404, json={"error": {"message": "No active device"}})
    )

    with pytest.raises(httpx.HTTPStatusError):
        await pause_playback()
