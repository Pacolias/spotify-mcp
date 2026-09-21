import httpx
import pytest
import respx

from spotify_mcp.spotify.client import (
    SPOTIFY_API_BASE,
    SpotifyPlaybackError,
    add_to_queue,
    pause_playback,
    resume_playback,
    seek_to_position,
    set_repeat_mode,
    set_shuffle,
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
async def test_pause_playback_raises_with_spotify_error_message(logged_in) -> None:
    # Found by testing against a real account with nothing playing: Spotify
    # returns a 404 with a specific reason, and the raw httpx exception
    # wasn't being turned into a message a tool caller could show the user.
    respx.put(f"{SPOTIFY_API_BASE}/me/player/pause").mock(
        return_value=httpx.Response(
            404,
            json={
                "error": {
                    "status": 404,
                    "message": "Player command failed: No active device found",
                    "reason": "NO_ACTIVE_DEVICE",
                }
            },
        )
    )

    with pytest.raises(SpotifyPlaybackError, match="No active device found"):
        await pause_playback()


@respx.mock
async def test_set_shuffle_sends_state_param(logged_in) -> None:
    route = respx.put(f"{SPOTIFY_API_BASE}/me/player/shuffle").mock(return_value=httpx.Response(200))

    await set_shuffle(True)

    assert route.calls.last.request.url.params["state"] == "true"


@respx.mock
async def test_set_repeat_mode_sends_state_param(logged_in) -> None:
    route = respx.put(f"{SPOTIFY_API_BASE}/me/player/repeat").mock(return_value=httpx.Response(200))

    await set_repeat_mode("track")

    assert route.calls.last.request.url.params["state"] == "track"


@respx.mock
async def test_seek_to_position_sends_position_param(logged_in) -> None:
    route = respx.put(f"{SPOTIFY_API_BASE}/me/player/seek").mock(return_value=httpx.Response(200))

    await seek_to_position(5000)

    assert route.calls.last.request.url.params["position_ms"] == "5000"
