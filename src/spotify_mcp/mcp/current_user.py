"""Who the current MCP request is for.

Tools resolve the user once and pass `user_id` explicitly to every Spotify
client call (journal 46, decision 2).
"""

from mcp.server.auth.middleware.auth_context import get_access_token
from sqlmodel import Session

from spotify_mcp.db import session as db_session
from spotify_mcp.spotify.auth import _only_local_user


def current_user_id() -> str:
    """The Spotify user ID of the caller: the `sub` of the request's verified
    access token. Over stdio there's no token, so it falls back to the single
    locally logged-in user (raises NotAuthenticatedError if there isn't one).
    """
    token = get_access_token()
    if token is not None and token.subject is not None:
        return token.subject
    with Session(db_session.engine) as session:
        return _only_local_user(session)
