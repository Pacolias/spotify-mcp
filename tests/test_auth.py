from datetime import timedelta

import httpx
import pytest
import respx
from sqlmodel import Session, select

from spotify_mcp.db.encryption import decrypt
from spotify_mcp.db.models import SpotifyCredentials
from spotify_mcp.spotify.auth import (
    SPOTIFY_TOKEN_URL,
    NotAuthenticatedError,
    get_valid_access_token,
)


async def test_raises_when_never_logged_in(db_engine, seed_user) -> None:
    with pytest.raises(NotAuthenticatedError):
        await get_valid_access_token("alice")


async def test_returns_token_unchanged_when_still_valid(db_engine, seed_user) -> None:
    seed_user("alice", access_token="still-valid-token", expires_in=timedelta(minutes=30))

    token = await get_valid_access_token("alice")

    assert token == "still-valid-token"


@respx.mock
async def test_refreshes_token_when_close_to_expiry(db_engine, seed_user) -> None:
    seed_user("alice", access_token="stale-token", expires_in=timedelta(seconds=10))
    refresh_route = respx.post(SPOTIFY_TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "refreshed-token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "user-read-currently-playing",
            },
        )
    )

    token = await get_valid_access_token("alice")

    assert token == "refreshed-token"
    # The stored refresh token was decrypted before being sent to Spotify.
    assert b"refresh_token=refresh-token" in refresh_route.calls.last.request.content
    with Session(db_engine) as session:
        stored = session.get(SpotifyCredentials, "alice")
        assert stored is not None
        assert decrypt(stored.encrypted_access_token) == "refreshed-token"


async def test_tokens_are_stored_encrypted(db_engine, seed_user) -> None:
    seed_user("alice", access_token="plain-access", refresh_token="plain-refresh")

    with Session(db_engine) as session:
        stored = session.exec(select(SpotifyCredentials)).one()

    assert "plain-access" not in stored.encrypted_access_token
    assert "plain-refresh" not in stored.encrypted_refresh_token


async def test_each_user_gets_their_own_token(db_engine, seed_user) -> None:
    seed_user("alice", access_token="alice-token")
    seed_user("bob", access_token="bob-token")

    assert await get_valid_access_token("alice") == "alice-token"
    assert await get_valid_access_token("bob") == "bob-token"


async def test_unknown_user_is_not_authenticated(db_engine, seed_user) -> None:
    seed_user("alice")

    with pytest.raises(NotAuthenticatedError):
        await get_valid_access_token("mallory")
