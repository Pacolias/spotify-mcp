from datetime import timedelta

import httpx
import pytest
import respx
from sqlmodel import Session

from spotify_mcp.db.models import SpotifyToken
from spotify_mcp.spotify.auth import (
    SPOTIFY_TOKEN_URL,
    NotAuthenticatedError,
    _utcnow,
    get_valid_access_token,
)


async def test_raises_when_never_logged_in(db_engine) -> None:
    with pytest.raises(NotAuthenticatedError):
        await get_valid_access_token()


async def test_returns_token_unchanged_when_still_valid(db_engine) -> None:
    with Session(db_engine) as session:
        session.add(
            SpotifyToken(
                id=1,
                access_token="still-valid-token",
                refresh_token="refresh-token",
                expires_at=_utcnow() + timedelta(minutes=30),
                scope="user-read-currently-playing",
            )
        )
        session.commit()

    token = await get_valid_access_token()

    assert token == "still-valid-token"


@respx.mock
async def test_refreshes_token_when_close_to_expiry(db_engine) -> None:
    with Session(db_engine) as session:
        session.add(
            SpotifyToken(
                id=1,
                access_token="stale-token",
                refresh_token="refresh-token",
                expires_at=_utcnow() + timedelta(seconds=10),
                scope="user-read-currently-playing",
            )
        )
        session.commit()

    respx.post(SPOTIFY_TOKEN_URL).mock(
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

    token = await get_valid_access_token()

    assert token == "refreshed-token"
    with Session(db_engine) as session:
        stored = session.get(SpotifyToken, 1)
        assert stored is not None
        assert stored.access_token == "refreshed-token"
