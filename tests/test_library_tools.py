"""Tests the tool layer in mcp/tools/library.py — see test_playback_tools.py
for why these monkeypatch the client functions instead of mocking HTTP.
"""

import spotify_mcp.mcp.tools.library as library_tools
from spotify_mcp.spotify.auth import NotAuthenticatedError
from spotify_mcp.spotify.client import SpotifyAPIError


async def test_liked_songs_formats_results(monkeypatch) -> None:
    async def fake_get_saved_tracks(limit, offset):
        return [{"name": "Track", "artists": ["Artist"], "id": "t1"}]

    monkeypatch.setattr(library_tools, "get_saved_tracks", fake_get_saved_tracks)

    result = await library_tools.liked_songs()

    assert result == "Track — Artist — id: t1"


async def test_liked_songs_reports_empty(monkeypatch) -> None:
    async def fake_get_saved_tracks(limit, offset):
        return []

    monkeypatch.setattr(library_tools, "get_saved_tracks", fake_get_saved_tracks)

    assert await library_tools.liked_songs() == "No liked songs found."


async def test_liked_songs_surfaces_not_authenticated(monkeypatch) -> None:
    async def fake_get_saved_tracks(limit, offset):
        raise NotAuthenticatedError("not logged in")

    monkeypatch.setattr(library_tools, "get_saved_tracks", fake_get_saved_tracks)

    assert await library_tools.liked_songs() == "not logged in"


async def test_like_tracks_reports_count(monkeypatch) -> None:
    async def fake_save_tracks(track_ids):
        assert track_ids == ["t1", "t2"]

    monkeypatch.setattr(library_tools, "save_tracks", fake_save_tracks)

    assert await library_tools.like_tracks(["t1", "t2"]) == "Saved 2 track(s) to Liked Songs."


async def test_like_tracks_surfaces_api_error(monkeypatch) -> None:
    async def fake_save_tracks(track_ids):
        raise SpotifyAPIError("Forbidden")

    monkeypatch.setattr(library_tools, "save_tracks", fake_save_tracks)

    result = await library_tools.like_tracks(["t1"])

    assert result == "Spotify API error: Forbidden"


async def test_like_tracks_surfaces_not_authenticated(monkeypatch) -> None:
    async def fake_save_tracks(track_ids):
        raise NotAuthenticatedError("not logged in")

    monkeypatch.setattr(library_tools, "save_tracks", fake_save_tracks)

    assert await library_tools.like_tracks(["t1"]) == "not logged in"


async def test_unlike_tracks_reports_count(monkeypatch) -> None:
    async def fake_remove_saved_tracks(track_ids):
        assert track_ids == ["t1"]

    monkeypatch.setattr(library_tools, "remove_saved_tracks", fake_remove_saved_tracks)

    result = await library_tools.unlike_tracks(["t1"])

    assert result == "Removed 1 track(s) from Liked Songs."


async def test_unlike_tracks_surfaces_api_error(monkeypatch) -> None:
    async def fake_remove_saved_tracks(track_ids):
        raise SpotifyAPIError("Forbidden")

    monkeypatch.setattr(library_tools, "remove_saved_tracks", fake_remove_saved_tracks)

    result = await library_tools.unlike_tracks(["t1"])

    assert result == "Spotify API error: Forbidden"
