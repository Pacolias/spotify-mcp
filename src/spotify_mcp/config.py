import sys

from cryptography.fernet import Fernet
from pydantic import SecretStr, ValidationError, field_validator
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
        "user-library-modify "
        "user-read-playback-state"
    )

    # SQLite locally, Postgres (Neon) in production (journal 48).
    database_url: str = "sqlite:///./spotify_mcp.db"

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_for_postgres(cls, value: str) -> str:
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value.removeprefix(prefix)
        return value

    # Public URLs of this server, as MCP clients see them. The issuer goes in
    # the `iss` claim of the tokens we issue; the MCP resource URL goes in
    # `aud`, so a token is only accepted by the server it was issued for.
    oauth_issuer_url: str = "http://127.0.0.1:8000"
    mcp_resource_url: str = "http://127.0.0.1:8000/mcp"

    # Header carrying the real client IP when behind a proxy that sets it and
    # can't be spoofed by the client, e.g. "true-client-ip" on Render (set by
    # Cloudflare, in front of it). X-Forwarded-For is deliberately not used:
    # Render appends to whatever the client sent, so its first entry can be
    # forged. Unset locally, where the connection's own address is the client.
    client_ip_header: str | None = None

    # Secret used to sign (HS256) the JWT access tokens this server issues to
    # MCP clients. Whoever has it can forge a token for any user. SecretStr
    # keeps it out of reprs/logs; read it with .get_secret_value().
    jwt_signing_key: SecretStr

    @field_validator("jwt_signing_key")
    @classmethod
    def _signing_key_long_enough(cls, value: SecretStr) -> SecretStr:
        # HS256 needs a key at least as long as its hash output: 256 bits.
        if len(value.get_secret_value().encode()) < 32:
            raise ValueError(
                "must be at least 32 bytes (256 bits). Generate one with:\n"
                '    python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )
        return value

    # Fernet key that encrypts users' Spotify tokens at rest (journal 42,
    # decision 5). Losing it means every user has to reconnect Spotify.
    token_encryption_key: SecretStr

    @field_validator("token_encryption_key")
    @classmethod
    def _valid_fernet_key(cls, value: SecretStr) -> SecretStr:
        try:
            Fernet(value.get_secret_value())
        except ValueError:
            raise ValueError(
                "must be a Fernet key (32 url-safe base64-encoded bytes). Generate one with:\n"
                '    python -c "from cryptography.fernet import Fernet; '
                'print(Fernet.generate_key().decode())"'
            ) from None
        return value


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
            # Field name and reason only: pydantic's own message echoes the
            # rejected value, and these values are secrets (signing key,
            # encryption key, a database URL with its password).
            problems = "\n".join(
                f"  {'.'.join(str(part) for part in err['loc'])}: {err['msg']}"
                for err in exc.errors()
            )
            print(f"Invalid configuration:\n{problems}", file=sys.stderr)
        sys.exit(1)


settings = _load_settings()
