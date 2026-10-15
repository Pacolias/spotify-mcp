import pytest
from pydantic import ValidationError

from spotify_mcp.config import Settings


@pytest.mark.parametrize(
    "given",
    [
        "postgres://user:pw@db.neon.tech/app?sslmode=require",
        "postgresql://user:pw@db.neon.tech/app?sslmode=require",
    ],
)
def test_postgres_urls_use_psycopg_3(given: str) -> None:
    settings = Settings(database_url=given)

    assert settings.database_url == (
        "postgresql+psycopg://user:pw@db.neon.tech/app?sslmode=require"
    )


def test_other_urls_are_left_alone() -> None:
    assert Settings(database_url="sqlite:///./x.db").database_url == "sqlite:///./x.db"
    explicit = "postgresql+psycopg://user:pw@host/app"
    assert Settings(database_url=explicit).database_url == explicit


def test_a_url_broken_across_lines_is_rejected_clearly() -> None:
    with pytest.raises(ValidationError, match="single line"):
        Settings(database_url="postgresql://user:pw@db.neon.te\n  ch/app")
