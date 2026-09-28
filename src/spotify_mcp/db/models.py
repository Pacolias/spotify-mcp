from datetime import datetime

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """Someone who has connected their Spotify account.

    Keyed by Spotify's user ID (the stable `id` from /v1/me, not the
    changeable display name). See journal 42, decision 1.
    """

    __tablename__ = "users"

    spotify_id: str = Field(primary_key=True)
    display_name: str | None = None
    created_at: datetime


class SpotifyCredentials(SQLModel, table=True):
    """A user's Spotify OAuth tokens, encrypted at rest (journal 42, decision 5).

    One row per user, replaced on every login/refresh. The token columns hold
    Fernet ciphertext; go through spotify_mcp.db.encryption to read/write them.
    """

    __tablename__ = "spotify_credentials"

    user_id: str = Field(primary_key=True, foreign_key="users.spotify_id")
    encrypted_access_token: str
    encrypted_refresh_token: str
    expires_at: datetime
    scope: str
