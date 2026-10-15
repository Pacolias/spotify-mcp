from collections.abc import Generator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect
from sqlmodel import Session, create_engine

from spotify_mcp.config import settings
from spotify_mcp.db.models import (  # noqa: F401 — registers the tables with SQLModel.metadata
    AuthorizationCode,
    OAuthClient,
    PendingAuthorization,
    RefreshToken,
    SpotifyCredentials,
    User,
)

# pool_pre_ping: Neon scales to zero and drops idle connections, so check a
# pooled connection is alive before handing it out.
engine = create_engine(settings.database_url, pool_pre_ping=True)

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"

# The first migration: the schema as it was when Alembic was introduced.
_BASELINE_REVISION = "0001"


def init_db(db_engine: Engine | None = None) -> None:
    """Bring the database schema up to date by applying Alembic migrations
    (journal 50). Runs at app startup."""
    db_engine = db_engine or engine
    with db_engine.begin() as connection:
        config = Config()
        config.set_main_option("script_location", str(MIGRATIONS_DIR))
        config.attributes["connection"] = connection

        tables = set(inspect(connection).get_table_names())
        if "alembic_version" not in tables and "users" in tables:
            # A database created by create_all before Alembic existed: its
            # tables already match the baseline, so record that instead of
            # trying to create them again.
            command.stamp(config, _BASELINE_REVISION)
        command.upgrade(config, "head")


def get_session() -> Generator[Session]:
    with Session(engine) as session:
        yield session
