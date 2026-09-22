import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta


def _utcnow() -> datetime:
    # Naive UTC on purpose: SQLite has no timezone-aware datetime type, so a
    # tz-aware value written here comes back naive on read, and Python can't
    # compare naive and aware datetimes. Keeping everything naive-but-UTC
    # avoids that mismatch.
    return datetime.now(UTC).replace(tzinfo=None)
import asyncio
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session

from spotify_mcp.config import settings
from spotify_mcp.db.models import SpotifyToken
from spotify_mcp.db.session import engine

router = APIRouter(prefix="/auth", tags=["auth"])

SPOTIFY_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"

# See spotify/client.py for why this is set explicitly.
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

# Maps OAuth `state` -> PKCE code_verifier for the short window between
# redirecting to Spotify and receiving the callback. An in-memory dict is
# fine for a single-user, single-process app; a multi-worker deployment
# would need a shared store (DB/Redis) instead.
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
    """Raised when a Spotify tool is called before /auth/login has completed."""


def _generate_code_verifier() -> str:
    return secrets.token_urlsafe(64)


def _generate_code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


@router.get("/login")
def login() -> RedirectResponse:
    """Start the OAuth2 Authorization Code + PKCE flow: redirect the user's
    browser to Spotify's consent screen."""
    code_verifier = _generate_code_verifier()
    code_challenge = _generate_code_challenge(code_verifier)
    state = secrets.token_urlsafe(16)
    _pending_logins[state] = code_verifier

    params = {
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "redirect_uri": settings.spotify_redirect_uri,
        "scope": settings.spotify_scopes,
        "code_challenge_method": "S256",
        "code_challenge": code_challenge,
        "state": state,
    }
    return RedirectResponse(f"{SPOTIFY_AUTHORIZE_URL}?{urlencode(params)}")


@router.get("/callback")
async def callback(
    code: str | None = None, state: str | None = None, error: str | None = None
) -> HTMLResponse:
    """Spotify redirects here after the user approves (or denies) access.
    Exchanges the authorization code for an access/refresh token pair."""
    if error:
        raise HTTPException(status_code=400, detail=f"Spotify authorization failed: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    code_verifier = _pending_logins.pop(state, None)
    if code_verifier is None:
        raise HTTPException(status_code=400, detail="Unknown or expired state")

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

    token = SpotifyToken(
        id=1,
        access_token=payload["access_token"],
        refresh_token=payload["refresh_token"],
        expires_at=_utcnow() + timedelta(seconds=payload["expires_in"]),
        scope=payload["scope"],
    )
    with Session(engine) as session:
        session.merge(token)
        session.commit()

    login_complete.set()
    return HTMLResponse(_SUCCESS_PAGE)


async def _refresh(token: SpotifyToken, session: Session) -> SpotifyToken:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(
            SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": token.refresh_token,
                "client_id": settings.spotify_client_id,
            },
        )
    response.raise_for_status()
    payload = response.json()

    token.access_token = payload["access_token"]
    token.expires_at = _utcnow() + timedelta(seconds=payload["expires_in"])
    # Spotify doesn't always rotate the refresh token — keep the old one if absent.
    if "refresh_token" in payload:
        token.refresh_token = payload["refresh_token"]

    session.add(token)
    session.commit()
    session.refresh(token)
    return token


async def get_valid_access_token() -> str:
    """Returns a Spotify access token guaranteed to be valid for at least
    30 more seconds, refreshing it first if needed. Used by every Spotify API
    call the MCP tools make."""
    with Session(engine) as session:
        token = session.get(SpotifyToken, 1)
        if token is None:
            raise NotAuthenticatedError("Not logged in — visit /auth/login first.")

        if token.expires_at <= _utcnow() + timedelta(seconds=30):
            token = await _refresh(token, session)

        return token.access_token
