import sys

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "spotify-mcp"

    spotify_client_id: str
    spotify_redirect_uri: str = "http://127.0.0.1:8000/auth/callback"
    # Space-separated OAuth scopes. Started minimal (principle of least
    # privilege) and grows as we add tools that need more Spotify permissions.
    # Requesting the full set needed for the rest of the planned tools
    # (personal data, playlists, playback control) in one go, to avoid
    # asking the user to re-login through the browser repeatedly.
    spotify_scopes: str = (
        "user-read-currently-playing "
        "user-top-read "
        "user-read-recently-played "
        "playlist-read-private "
        "playlist-modify-private "
        "playlist-modify-public "
        "user-modify-playback-state "
        "user-library-read "
        "user-library-modify"
    )

    database_url: str = "sqlite:///./spotify_mcp.db"


def _load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        missing = [str(err["loc"][0]) for err in exc.errors() if err["type"] == "missing"]
        if missing:
            print(
                f"Missing required configuration: {', '.join(missing)}\n\n"
                "Copy .env.example to .env and fill in the missing value(s):\n"
                "    cp .env.example .env\n\n"
                "See the Setup section in README.md for details.",
                file=sys.stderr,
            )
        else:
            print(f"Invalid configuration:\n{exc}", file=sys.stderr)
        sys.exit(1)


settings = _load_settings()
