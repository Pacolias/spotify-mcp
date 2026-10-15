from datetime import timedelta

import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken
from sqlmodel import Session, SQLModel, create_engine

import spotify_mcp.db.session as db_session
import spotify_mcp.spotify.auth as auth_module
from spotify_mcp.db.encryption import encrypt
from spotify_mcp.db.models import SpotifyCredentials, User
from spotify_mcp.spotify.auth import _utcnow

TEST_USER_ID = "test-user"


@pytest.fixture(autouse=True)
def authenticated_user():
    """Every test runs as if an MCP request carried a verified access token
    for TEST_USER_ID, so tools never fall back to whatever user happens to be
    in the developer's local database."""
    token = AccessToken(
        token="test-token", client_id="test-client", scopes=[], subject=TEST_USER_ID
    )
    reset = auth_context_var.set(AuthenticatedUser(token))
    yield
    auth_context_var.reset(reset)


@pytest.fixture
def db_engine(tmp_path, monkeypatch):
    """A throwaway SQLite database for a single test, isolated from the
    real spotify_mcp.db used during manual/local runs."""
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    SQLModel.metadata.create_all(engine)

    # db.session and spotify.auth each did `from ... import engine`, which
    # binds their own local name at import time — patching db_session.engine
    # alone wouldn't affect auth_module's already-bound reference.
    monkeypatch.setattr(db_session, "engine", engine)
    monkeypatch.setattr(auth_module, "engine", engine)

    yield engine
    engine.dispose()


@pytest.fixture
def logged_in(db_engine) -> None:
    """Seeds a valid (non-expiring-soon) token, as if /auth/login had already
    completed, for tests that call Spotify-API-backed code."""
    _seed_user(db_engine, "test-user", access_token="test-access-token")


@pytest.fixture
def seed_user(db_engine):
    """Returns a function that stores a user and their Spotify tokens."""

    def seed(spotify_id: str, **kwargs) -> None:
        _seed_user(db_engine, spotify_id, **kwargs)

    return seed


def _seed_user(
    engine,
    spotify_id: str,
    access_token: str = "access-token",
    refresh_token: str = "refresh-token",
    expires_in: timedelta = timedelta(hours=1),
) -> None:
    """Store a user and their (encrypted) Spotify tokens, as a login would."""
    with Session(engine) as session:
        session.add(User(spotify_id=spotify_id, created_at=_utcnow()))
        session.add(
            SpotifyCredentials(
                user_id=spotify_id,
                encrypted_access_token=encrypt(access_token),
                encrypted_refresh_token=encrypt(refresh_token),
                expires_at=_utcnow() + expires_in,
                scope="user-read-currently-playing",
            )
        )
        session.commit()
