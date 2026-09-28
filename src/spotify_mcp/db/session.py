from collections.abc import Generator

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from spotify_mcp.config import settings
from spotify_mcp.db.models import (  # noqa: F401 — registers the tables with SQLModel.metadata
    SpotifyCredentials,
    User,
)

engine = create_engine(settings.database_url)


def init_db() -> None:
    with engine.begin() as connection:
        # Pre-multi-user table: a single row of *unencrypted* Spotify tokens.
        # Dropped rather than migrated so plaintext tokens don't linger on
        # disk; the user logs in once more to repopulate the new tables.
        connection.execute(text("DROP TABLE IF EXISTS spotifytoken"))
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session]:
    with Session(engine) as session:
        yield session
