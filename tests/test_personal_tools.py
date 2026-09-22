"""Tests the tool layer in mcp/tools/personal.py — see test_playback_tools.py
for why these monkeypatch the client functions instead of mocking HTTP.
"""

import spotify_mcp.mcp.tools.personal as personal_tools
from spotify_mcp.spotify.auth import NotAuthenticatedError


async def test_top_tracks_formats_results(monkeypatch) -> None:
    async def fake_get_top_tracks(limit, time_range):
        return [{"name": "Track", "artists": ["Artist"], "album": "Album"}]

    monkeypatch.setattr(personal_tools, "get_top_tracks", fake_get_top_tracks)

    result = await personal_tools.top_tracks()

    assert result == "Track — Artist (Album)"


async def test_top_tracks_reports_empty(monkeypatch) -> None:
    async def fake_get_top_tracks(limit, time_range):
        return []

    monkeypatch.setattr(personal_tools, "get_top_tracks", fake_get_top_tracks)

    assert await personal_tools.top_tracks() == "No top tracks available for this time range."


async def test_top_tracks_surfaces_not_authenticated(monkeypatch) -> None:
    async def fake_get_top_tracks(limit, time_range):
        raise NotAuthenticatedError("not logged in")

    monkeypatch.setattr(personal_tools, "get_top_tracks", fake_get_top_tracks)

    assert await personal_tools.top_tracks() == "not logged in"


async def test_top_artists_includes_genres_when_present(monkeypatch) -> None:
    async def fake_get_top_artists(limit, time_range):
        return [{"name": "Artist A", "genres": ["synthwave", "electronic"]}]

    monkeypatch.setattr(personal_tools, "get_top_artists", fake_get_top_artists)

    result = await personal_tools.top_artists()

    assert result == "Artist A (synthwave, electronic)"


async def test_top_artists_omits_parens_when_no_genres(monkeypatch) -> None:
    async def fake_get_top_artists(limit, time_range):
        return [{"name": "Artist A", "genres": []}]

    monkeypatch.setattr(personal_tools, "get_top_artists", fake_get_top_artists)

    result = await personal_tools.top_artists()

    assert result == "Artist A"


async def test_top_artists_reports_empty(monkeypatch) -> None:
    async def fake_get_top_artists(limit, time_range):
        return []

    monkeypatch.setattr(personal_tools, "get_top_artists", fake_get_top_artists)

    assert await personal_tools.top_artists() == "No top artists available for this time range."


async def test_recently_played_formats_results(monkeypatch) -> None:
    async def fake_get_recently_played(limit):
        return [{"played_at": "2026-09-22T10:00:00Z", "name": "Track", "artists": ["Artist"]}]

    monkeypatch.setattr(personal_tools, "get_recently_played", fake_get_recently_played)

    result = await personal_tools.recently_played()

    assert result == "2026-09-22T10:00:00Z — Track — Artist"


async def test_recently_played_reports_empty(monkeypatch) -> None:
    async def fake_get_recently_played(limit):
        return []

    monkeypatch.setattr(personal_tools, "get_recently_played", fake_get_recently_played)

    assert await personal_tools.recently_played() == "No recent playback history."
