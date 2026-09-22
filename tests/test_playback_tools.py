"""Tests the tool layer in mcp/tools/playback.py: message formatting and
exception-to-string mapping. The underlying Spotify client calls are already
covered by tests/test_playback_client.py, so these monkeypatch the client
functions directly rather than re-mocking HTTP.
"""

import spotify_mcp.mcp.tools.playback as playback_tools
from spotify_mcp.spotify.auth import NotAuthenticatedError
from spotify_mcp.spotify.client import SpotifyAPIError, SpotifyPlaybackError


async def test_now_playing_formats_active_track(monkeypatch) -> None:
    async def fake_get_currently_playing():
        return {
            "name": "Track",
            "artists": ["Artist"],
            "album": "Album",
            "is_playing": True,
            "url": "https://open.spotify.com/track/t1",
        }

    monkeypatch.setattr(playback_tools, "get_currently_playing", fake_get_currently_playing)

    result = await playback_tools.now_playing()

    assert result == "Playing: Track — Artist (Album): https://open.spotify.com/track/t1"


async def test_now_playing_formats_paused_track(monkeypatch) -> None:
    async def fake_get_currently_playing():
        return {
            "name": "Track",
            "artists": ["Artist"],
            "album": "Album",
            "is_playing": False,
            "url": "https://open.spotify.com/track/t1",
        }

    monkeypatch.setattr(playback_tools, "get_currently_playing", fake_get_currently_playing)

    result = await playback_tools.now_playing()

    assert result.startswith("Paused:")


async def test_now_playing_reports_nothing_playing(monkeypatch) -> None:
    async def fake_get_currently_playing():
        return None

    monkeypatch.setattr(playback_tools, "get_currently_playing", fake_get_currently_playing)

    assert await playback_tools.now_playing() == "Nothing is currently playing."


async def test_now_playing_surfaces_not_authenticated(monkeypatch) -> None:
    async def fake_get_currently_playing():
        raise NotAuthenticatedError("not logged in")

    monkeypatch.setattr(playback_tools, "get_currently_playing", fake_get_currently_playing)

    assert await playback_tools.now_playing() == "not logged in"


async def test_pause_reports_success(monkeypatch) -> None:
    async def fake_pause_playback():
        return None

    monkeypatch.setattr(playback_tools, "pause_playback", fake_pause_playback)

    assert await playback_tools.pause() == "Paused."


async def test_pause_surfaces_playback_error(monkeypatch) -> None:
    async def fake_pause_playback():
        raise SpotifyPlaybackError("No active device found")

    monkeypatch.setattr(playback_tools, "pause_playback", fake_pause_playback)

    assert await playback_tools.pause() == "No active device found"


async def test_resume_reports_success(monkeypatch) -> None:
    async def fake_resume_playback():
        return None

    monkeypatch.setattr(playback_tools, "resume_playback", fake_resume_playback)

    assert await playback_tools.resume() == "Resumed playback."


async def test_skip_next_reports_success(monkeypatch) -> None:
    async def fake_skip_to_next():
        return None

    monkeypatch.setattr(playback_tools, "skip_to_next", fake_skip_to_next)

    assert await playback_tools.skip_next() == "Skipped to next track."


async def test_skip_previous_reports_success(monkeypatch) -> None:
    async def fake_skip_to_previous():
        return None

    monkeypatch.setattr(playback_tools, "skip_to_previous", fake_skip_to_previous)

    assert await playback_tools.skip_previous() == "Skipped to previous track."


async def test_set_playback_volume_rejects_out_of_range() -> None:
    assert await playback_tools.set_playback_volume(150) == (
        "volume_percent must be between 0 and 100."
    )
    assert await playback_tools.set_playback_volume(-1) == (
        "volume_percent must be between 0 and 100."
    )


async def test_set_playback_volume_reports_success(monkeypatch) -> None:
    async def fake_set_volume(volume_percent):
        assert volume_percent == 42

    monkeypatch.setattr(playback_tools, "set_volume", fake_set_volume)

    assert await playback_tools.set_playback_volume(42) == "Volume set to 42%."


async def test_queue_track_reports_success(monkeypatch) -> None:
    async def fake_add_to_queue(track_id):
        assert track_id == "t1"

    monkeypatch.setattr(playback_tools, "add_to_queue", fake_add_to_queue)

    assert await playback_tools.queue_track("t1") == "Track added to queue."


async def test_shuffle_reports_on_and_off(monkeypatch) -> None:
    async def fake_set_shuffle(enabled):
        return None

    monkeypatch.setattr(playback_tools, "set_shuffle", fake_set_shuffle)

    assert await playback_tools.shuffle(True) == "Shuffle on."
    assert await playback_tools.shuffle(False) == "Shuffle off."


async def test_repeat_mode_rejects_invalid_mode() -> None:
    assert await playback_tools.repeat_mode("loud") == "mode must be one of: track, context, off."


async def test_repeat_mode_reports_success(monkeypatch) -> None:
    async def fake_set_repeat_mode(mode):
        assert mode == "context"

    monkeypatch.setattr(playback_tools, "set_repeat_mode", fake_set_repeat_mode)

    assert await playback_tools.repeat_mode("context") == "Repeat mode set to 'context'."


async def test_seek_rejects_negative_position() -> None:
    assert await playback_tools.seek(-1) == "position_ms must be 0 or greater."


async def test_seek_reports_success(monkeypatch) -> None:
    async def fake_seek_to_position(position_ms):
        assert position_ms == 5000

    monkeypatch.setattr(playback_tools, "seek_to_position", fake_seek_to_position)

    assert await playback_tools.seek(5000) == "Seeked to 5000ms."


async def test_list_devices_formats_active_device(monkeypatch) -> None:
    async def fake_get_devices():
        return [
            {"id": "d1", "name": "Kitchen Speaker", "type": "Speaker", "is_active": True},
            {"id": "d2", "name": "Phone", "type": "Smartphone", "is_active": False},
        ]

    monkeypatch.setattr(playback_tools, "get_devices", fake_get_devices)

    result = await playback_tools.list_devices()

    assert "Kitchen Speaker (Speaker) — active — id: d1" in result
    assert "Phone (Smartphone) — id: d2" in result


async def test_list_devices_reports_none_found(monkeypatch) -> None:
    async def fake_get_devices():
        return []

    monkeypatch.setattr(playback_tools, "get_devices", fake_get_devices)

    result = await playback_tools.list_devices()

    assert "No devices found" in result


async def test_list_devices_surfaces_api_error(monkeypatch) -> None:
    async def fake_get_devices():
        raise SpotifyAPIError("boom")

    monkeypatch.setattr(playback_tools, "get_devices", fake_get_devices)

    assert await playback_tools.list_devices() == "boom"


async def test_activate_device_reports_success(monkeypatch) -> None:
    async def fake_transfer_playback(device_id, play):
        assert device_id == "d1"
        assert play is True

    monkeypatch.setattr(playback_tools, "transfer_playback", fake_transfer_playback)

    assert await playback_tools.activate_device("d1") == "Switched playback to device d1."
