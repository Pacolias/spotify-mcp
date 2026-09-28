from sqlalchemy import inspect, text

from spotify_mcp.db.session import init_db


def test_init_db_drops_the_old_plaintext_token_table(db_engine) -> None:
    with db_engine.begin() as connection:
        connection.execute(text("CREATE TABLE spotifytoken (id INTEGER, access_token TEXT)"))

    init_db()

    tables = inspect(db_engine).get_table_names()
    assert "spotifytoken" not in tables
    assert {"users", "spotify_credentials"} <= set(tables)
