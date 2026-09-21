from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from spotify_mcp.config import settings
from spotify_mcp.db.models import SpotifyToken  # noqa: F401 — registers the table with SQLModel.metadata

engine = create_engine(settings.database_url)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session]:
    with Session(engine) as session:
        yield session
