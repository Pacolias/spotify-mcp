"""Who the current MCP request is for.

Tools resolve the user once and pass `user_id` explicitly to every Spotify
client call (journal 46, decision 2).
"""

from mcp.server.auth.middleware.auth_context import get_access_token

from spotify_mcp.spotify.auth import NotAuthenticatedError


def current_user_id() -> str:
    """The Spotify user ID of the caller: the `sub` of the request's verified
    access token. The SDK rejects /mcp requests without a valid token before
    any tool runs, so a missing one here means a tool ran outside a request.
    """
    token = get_access_token()
    if token is None or token.subject is None:
        raise NotAuthenticatedError("No authenticated user for this request.")
    return token.subject
