"""Tests the tool layer in mcp/tools/playlists.py not already covered by
test_playlist_tools_formatting.py — see test_playback_tools.py for why these
monkeypatch the client functions instead of mocking HTTP.
"""

import spotify_mcp.mcp.tools.playlists as playlist_tools
from spotify_mcp.spotify.auth import NotAuthenticatedError


async def test_list_user_playlists_formats_results(monkeypatch) -> None:
    async def fake_list_playlists(limit):
        return [{"name": "Chill", "track_count": 10, "public": True, "id": "p1"}]

    monkeypatch.setattr(playlist_tools, "list_playlists", fake_list_playlists)

    result = await playlist_tools.list_user_playlists()

    assert result == "Chill (10 tracks, public) — id: p1"


async def test_list_user_playlists_marks_private(monkeypatch) -> None:
    async def fake_list_playlists(limit):
        return [{"name": "Secret", "track_count": 1, "public": False, "id": "p2"}]

    monkeypatch.setattr(playlist_tools, "list_playlists", fake_list_playlists)

    result = await playlist_tools.list_user_playlists()

    assert "private" in result


async def test_list_user_playlists_reports_empty(monkeypatch) -> None:
    async def fake_list_playlists(limit):
        return []

    monkeypatch.setattr(playlist_tools, "list_playlists", fake_list_playlists)

    assert await playlist_tools.list_user_playlists() == "No playlists found."


async def test_list_user_playlists_surfaces_not_authenticated(monkeypatch) -> None:
    async def fake_list_playlists(limit):
        raise NotAuthenticatedError("not logged in")

    monkeypatch.setattr(playlist_tools, "list_playlists", fake_list_playlists)

    assert await playlist_tools.list_user_playlists() == "not logged in"


async def test_playlist_tracks_reports_empty(monkeypatch) -> None:
    async def fake_get_playlist_tracks(playlist_id, limit):
        return []

    monkeypatch.setattr(playlist_tools, "get_playlist_tracks", fake_get_playlist_tracks)

    assert await playlist_tools.playlist_tracks("p1") == "This playlist has no tracks."


async def test_create_user_playlist_formats_result(monkeypatch) -> None:
    async def fake_create_playlist(name, description, public):
        return {"name": name, "id": "p1", "url": "https://open.spotify.com/playlist/p1"}

    monkeypatch.setattr(playlist_tools, "create_playlist", fake_create_playlist)

    result = await playlist_tools.create_user_playlist("My Mix")

    assert result == "Created playlist 'My Mix' — id: p1 — https://open.spotify.com/playlist/p1"


async def test_create_user_playlist_surfaces_not_authenticated(monkeypatch) -> None:
    async def fake_create_playlist(name, description, public):
        raise NotAuthenticatedError("not logged in")

    monkeypatch.setattr(playlist_tools, "create_playlist", fake_create_playlist)

    assert await playlist_tools.create_user_playlist("My Mix") == "not logged in"


async def test_add_tracks_reports_count(monkeypatch) -> None:
    async def fake_add_tracks_to_playlist(playlist_id, track_ids):
        assert playlist_id == "p1"
        assert track_ids == ["t1", "t2"]

    monkeypatch.setattr(playlist_tools, "add_tracks_to_playlist", fake_add_tracks_to_playlist)

    result = await playlist_tools.add_tracks("p1", ["t1", "t2"])

    assert result == "Added 2 track(s) to playlist p1."


async def test_remove_tracks_reports_count(monkeypatch) -> None:
    async def fake_remove_tracks_from_playlist(playlist_id, track_ids):
        assert playlist_id == "p1"
        assert track_ids == ["t1"]

    monkeypatch.setattr(
        playlist_tools, "remove_tracks_from_playlist", fake_remove_tracks_from_playlist
    )

    result = await playlist_tools.remove_tracks("p1", ["t1"])

    assert result == "Removed 1 track(s) from playlist p1."


async def test_find_playlists_strips_html_from_description(monkeypatch) -> None:
    async def fake_search_playlists(query, limit):
        return [
            {
                "name": "Focus",
                "owner": "Spotify",
                "id": "p1",
                "url": "https://open.spotify.com/playlist/p1",
                "description": "Deep <b>focus</b> beats &amp; more",
            }
        ]

    monkeypatch.setattr(playlist_tools, "search_playlists", fake_search_playlists)

    result = await playlist_tools.find_playlists("focus")

    assert "<b>" not in result
    assert "Deep focus beats &amp; more" in result


async def test_find_playlists_reports_empty(monkeypatch) -> None:
    async def fake_search_playlists(query, limit):
        return []

    monkeypatch.setattr(playlist_tools, "search_playlists", fake_search_playlists)

    assert await playlist_tools.find_playlists("nothing") == "No playlists found for 'nothing'."
