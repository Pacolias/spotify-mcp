import asyncio
import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from spotify_mcp.config import settings
from spotify_mcp.db.encryption import decrypt, encrypt
from spotify_mcp.db.models import SpotifyCredentials, User
from spotify_mcp.db.session import engine


def _utcnow() -> datetime:
    # Naive UTC on purpose: SQLite has no timezone-aware datetime type, so a
    # tz-aware value written here comes back naive on read, and Python can't
    # compare naive and aware datetimes. Keeping everything naive-but-UTC
    # avoids that mismatch.
    return datetime.now(UTC).replace(tzinfo=None)


router = APIRouter(prefix="/auth", tags=["auth"])

SPOTIFY_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_ME_URL = "https://api.spotify.com/v1/me"

# See spotify/client.py for why this is set explicitly.
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

# Maps OAuth `state` -> PKCE code_verifier for the short window between
# redirecting to Spotify and receiving the callback, for the local `login`
# command. The remote server's flow will keep this in the database instead
# (journal 42, decision 7).
_pending_logins: dict[str, str] = {}

# Set once a login round-trip finishes successfully. Lets `spotify-mcp login`
# (spotify_mcp/cli.py) know it can stop waiting and shut the server down,
# instead of the user having to notice success and Ctrl+C manually.
login_complete = asyncio.Event()

_SUCCESS_PAGE = """\
<!doctype html>
<html>
  <head><title>spotify-mcp</title></head>
  <body style="font-family: system-ui, sans-serif; text-align: center; padding-top: 4rem;">
    <h1>✅ Logged in to Spotify</h1>
    <p>You can close this tab and go back to your terminal.</p>
  </body>
</html>
"""


class NotAuthenticatedError(Exception):
    """Raised when a Spotify tool is called for a user with no stored Spotify login."""


def generate_code_verifier() -> str:
    return secrets.token_urlsafe(64)


def generate_code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def build_authorize_url(state: str, code_challenge: str) -> str:
    """Spotify consent-screen URL for an Authorization Code + PKCE login."""
    params = {
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "redirect_uri": settings.spotify_redirect_uri,
        "scope": settings.spotify_scopes,
        "code_challenge_method": "S256",
        "code_challenge": code_challenge,
        "state": state,
    }
    return f"{SPOTIFY_AUTHORIZE_URL}?{urlencode(params)}"


async def complete_login(code: str, code_verifier: str) -> str:
    """Finish a Spotify login: exchange the authorization code for tokens, find
    out who logged in, and store them (encrypted) under that user.

    Shared by the local `login` command's callback and the MCP authorization
    server (spotify_mcp/oauth/provider.py). Returns the Spotify user ID.
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(
            SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.spotify_redirect_uri,
                "client_id": settings.spotify_client_id,
                "code_verifier": code_verifier,
            },
        )
        response.raise_for_status()
        payload = response.json()

        # Who just logged in: tokens are stored per Spotify user.
        me_response = await client.get(
            SPOTIFY_ME_URL, headers={"Authorization": f"Bearer {payload['access_token']}"}
        )
        me_response.raise_for_status()
        me = me_response.json()

    user_id = str(me["id"])
    with Session(engine) as session:
        user = session.get(User, user_id) or User(spotify_id=user_id, created_at=_utcnow())
        user.display_name = me.get("display_name")
        session.add(user)
        session.merge(
            SpotifyCredentials(
                user_id=user_id,
                encrypted_access_token=encrypt(payload["access_token"]),
                encrypted_refresh_token=encrypt(payload["refresh_token"]),
                expires_at=_utcnow() + timedelta(seconds=payload["expires_in"]),
                scope=payload["scope"],
            )
        )
        session.commit()
    return user_id


@router.get("/login")
def login() -> RedirectResponse:
    """Start the OAuth2 Authorization Code + PKCE flow: redirect the user's
    browser to Spotify's consent screen."""
    code_verifier = generate_code_verifier()
    state = secrets.token_urlsafe(16)
    _pending_logins[state] = code_verifier
    return RedirectResponse(build_authorize_url(state, generate_code_challenge(code_verifier)))


def is_local_login(state: str) -> bool:
    """Whether `state` belongs to a login started by `spotify-mcp login`."""
    return state in _pending_logins


async def finish_local_login(code: str | None, state: str, error: str | None) -> HTMLResponse:
    """The `spotify-mcp login` side of Spotify's callback (the route lives in
    spotify_mcp/main.py). Exchanges the authorization code for tokens."""
    code_verifier = _pending_logins.pop(state)
    if error:
        raise HTTPException(status_code=400, detail=f"Spotify authorization failed: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")

    await complete_login(code, code_verifier)

    login_complete.set()
    return HTMLResponse(_SUCCESS_PAGE)


async def _refresh(credentials: SpotifyCredentials, session: Session) -> str:
    """Get a new Spotify access token, store it, and return it (in plaintext)."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(
            SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": decrypt(credentials.encrypted_refresh_token),
                "client_id": settings.spotify_client_id,
            },
        )
    response.raise_for_status()
    payload = response.json()

    credentials.encrypted_access_token = encrypt(payload["access_token"])
    credentials.expires_at = _utcnow() + timedelta(seconds=payload["expires_in"])
    # Spotify doesn't always rotate the refresh token — keep the old one if absent.
    if "refresh_token" in payload:
        credentials.encrypted_refresh_token = encrypt(payload["refresh_token"])

    session.add(credentials)
    session.commit()
    return str(payload["access_token"])


def _only_local_user(session: Session) -> str:
    """The local stdio server has no authenticated caller, so it acts for the
    single user stored in the database."""
    user_ids = session.exec(select(SpotifyCredentials.user_id).limit(2)).all()
    if not user_ids:
        raise NotAuthenticatedError("Not logged in — run `spotify-mcp login` first.")
    if len(user_ids) > 1:
        raise NotAuthenticatedError(
            "More than one Spotify user is stored; the local server needs exactly one."
        )
    return user_ids[0]


async def get_valid_access_token(user_id: str | None = None) -> str:
    """Returns a Spotify access token for `user_id`, guaranteed to be valid
    for at least 30 more seconds, refreshing it first if needed. Used by every
    Spotify API call the MCP tools make.

    `user_id=None` means the local stdio server's single user.
    """
    with Session(engine) as session:
        if user_id is None:
            user_id = _only_local_user(session)

        credentials = session.get(SpotifyCredentials, user_id)
        if credentials is None:
            raise NotAuthenticatedError("This Spotify account isn't connected — log in first.")

        if credentials.expires_at <= _utcnow() + timedelta(seconds=30):
            return await _refresh(credentials, session)

        return decrypt(credentials.encrypted_access_token)
