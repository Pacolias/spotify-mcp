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


# --- OAuth authorization server (journal 41, 42) ------------------------------
# State for OAuth #1, where MCP hosts (e.g. Claude) are the clients and this
# server is the authorization server. Space-separated `scopes` columns follow
# the OAuth wire format. Timestamps are naive UTC, like the rest of the schema.


class OAuthClient(SQLModel, table=True):
    """An MCP host registered through dynamic client registration.

    The SDK's OAuthClientInformationFull is stored as JSON in one column: we
    never query its fields, and the SDK owns that schema (journal 42, item 6).
    """

    __tablename__ = "oauth_clients"

    client_id: str = Field(primary_key=True)
    client_info: str
    created_at: datetime


class PendingAuthorization(SQLModel, table=True):
    """An MCP client's /authorize request, parked while the user is on
    Spotify's consent screen (journal 42, item 7).

    Keyed by the random `state` we send to Spotify. `client_state` is the
    MCP client's own `state`, echoed back to it at the end.
    """

    __tablename__ = "pending_authorizations"

    state: str = Field(primary_key=True)
    client_id: str = Field(foreign_key="oauth_clients.client_id")
    client_state: str | None = None
    redirect_uri: str
    redirect_uri_provided_explicitly: bool
    code_challenge: str
    scopes: str
    resource: str | None = None
    # PKCE verifier for OAuth #2 (us -> Spotify). Short-lived and single use.
    spotify_code_verifier: str
    expires_at: datetime


class AuthorizationCode(SQLModel, table=True):
    """A single-use code handed to the MCP client after login, stored only as
    a SHA-256 hash (journal 42, decision 4)."""

    __tablename__ = "authorization_codes"

    code_hash: str = Field(primary_key=True)
    client_id: str = Field(foreign_key="oauth_clients.client_id")
    user_id: str = Field(foreign_key="users.spotify_id")
    redirect_uri: str
    redirect_uri_provided_explicitly: bool
    code_challenge: str
    scopes: str
    resource: str | None = None
    expires_at: datetime


class RefreshToken(SQLModel, table=True):
    """An opaque refresh token, stored only as a SHA-256 hash (journal 42,
    decisions 3 and 4).

    Rotated on every use: the old row is kept with `rotated_at` set, so if it
    is ever presented again we know it leaked and revoke the whole grant.
    """

    __tablename__ = "refresh_tokens"

    token_hash: str = Field(primary_key=True)
    client_id: str = Field(foreign_key="oauth_clients.client_id", index=True)
    user_id: str = Field(foreign_key="users.spotify_id", index=True)
    scopes: str
    resource: str | None = None
    expires_at: datetime
    rotated_at: datetime | None = None
