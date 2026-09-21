from datetime import datetime

from sqlmodel import Field, SQLModel


class SpotifyToken(SQLModel, table=True):
    """The logged-in user's Spotify OAuth tokens.

    Single-user app: there is only ever one row, fixed at id=1, replaced
    on every login/refresh rather than accumulating history.
    """

    id: int = Field(default=1, primary_key=True)
    access_token: str
    refresh_token: str
    expires_at: datetime
    scope: str
