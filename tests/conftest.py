import pytest
from sqlmodel import SQLModel, create_engine

import spotify_mcp.db.session as db_session
import spotify_mcp.spotify.auth as auth_module


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
