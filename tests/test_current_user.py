import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var

import spotify_mcp.mcp.tools.playback as playback_tools
from spotify_mcp.mcp.current_user import current_user_id
from spotify_mcp.spotify.auth import NotAuthenticatedError


def test_uses_the_subject_of_the_verified_access_token() -> None:
    assert current_user_id() == "test-user"


def test_without_a_token_falls_back_to_the_single_local_user(seed_user) -> None:
    seed_user("local-user")
    auth_context_var.set(None)

    assert current_user_id() == "local-user"


def test_without_a_token_or_local_user_raises(db_engine) -> None:
    auth_context_var.set(None)

    with pytest.raises(NotAuthenticatedError):
        current_user_id()


async def test_tools_pass_the_callers_user_id_to_spotify(monkeypatch) -> None:
    seen = []

    async def fake_pause_playback(user_id):
        seen.append(user_id)

    monkeypatch.setattr(playback_tools, "pause_playback", fake_pause_playback)

    await playback_tools.pause()

    assert seen == ["test-user"]
