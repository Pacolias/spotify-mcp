from datetime import timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine

import spotify_mcp.db.session as db_session
import spotify_mcp.spotify.auth as auth_module
from spotify_mcp.db.models import SpotifyToken
from spotify_mcp.spotify.auth import _utcnow


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

    return engine


@pytest.fixture
def logged_in(db_engine) -> None:
    """Seeds a valid (non-expiring-soon) token, as if /auth/login had already
    completed, for tests that call Spotify-API-backed code."""
    with Session(db_engine) as session:
        session.add(
            SpotifyToken(
                id=1,
                access_token="test-access-token",
                refresh_token="test-refresh-token",
                expires_at=_utcnow() + timedelta(hours=1),
                scope="user-read-currently-playing",
            )
        )
        session.commit()
