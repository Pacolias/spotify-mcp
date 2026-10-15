"""init_db applies the Alembic migrations (journal 50)."""

import os

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text
from sqlmodel import SQLModel, create_engine

from spotify_mcp.config import Settings
from spotify_mcp.db.session import init_db

APP_TABLES = {
    "users",
    "spotify_credentials",
    "oauth_clients",
    "pending_authorizations",
    "authorization_codes",
    "refresh_tokens",
}


@pytest.fixture
def empty_engine(tmp_path):
    """A database with no tables at all (SQLite, or TEST_DATABASE_URL)."""
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        engine = create_engine(Settings(database_url=url).database_url)
        SQLModel.metadata.drop_all(engine)
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
    else:
        engine = create_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    yield engine
    engine.dispose()


def _revision(engine) -> str | None:
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def test_migrations_create_every_table(empty_engine) -> None:
    init_db(empty_engine)

    assert APP_TABLES <= set(inspect(empty_engine).get_table_names())
    assert _revision(empty_engine) is not None


def test_migrations_match_the_models_exactly(empty_engine) -> None:
    """Catches a model change that was never turned into a migration."""
    init_db(empty_engine)

    with empty_engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), SQLModel.metadata)

    assert diff == []


def test_running_twice_is_harmless(empty_engine) -> None:
    init_db(empty_engine)
    revision = _revision(empty_engine)

    init_db(empty_engine)

    assert _revision(empty_engine) == revision


def test_a_database_from_before_alembic_is_adopted(empty_engine) -> None:
    # Created by create_all, as every database was before migrations.
    SQLModel.metadata.create_all(empty_engine)

    init_db(empty_engine)

    assert _revision(empty_engine) is not None
