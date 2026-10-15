"""Alembic environment (journal 50).

Runs against the app's own engine (settings.database_url), or against a
connection handed in through `config.attributes["connection"]` (used by
init_db and the tests).
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlmodel import SQLModel

from spotify_mcp.db import models  # noqa: F401 — registers the tables with SQLModel.metadata
from spotify_mcp.db import session as db_session

config = context.config

# Only when run from the CLI with alembic.ini: don't let a programmatic
# upgrade at app startup reconfigure the server's logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def _run(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # SQLite can't ALTER most things in place; batch mode recreates the
        # table instead, so future migrations also work on the local DB.
        render_as_batch=connection.dialect.name == "sqlite",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    context.configure(
        url=db_session.engine.url, target_metadata=target_metadata, literal_binds=True
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        _run(connection)
        return
    with db_session.engine.begin() as connection:
        _run(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
