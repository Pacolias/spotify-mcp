"""Tokens this server issues to MCP clients.

- Access tokens are JWTs (HS256), verified by signature alone. See journal 42.
- Refresh tokens and authorization codes are opaque random strings, stored
  only as SHA-256 hashes.
"""

import hashlib
import secrets
import time
import uuid

import jwt
from mcp.server.auth.provider import AccessToken

from spotify_mcp.config import settings

ACCESS_TOKEN_LIFETIME_SECONDS = 60 * 60
_ALGORITHM = "HS256"
_REQUIRED_CLAIMS = ["exp", "iat", "iss", "aud", "sub", "client_id"]


def _key() -> str:
    return settings.jwt_signing_key.get_secret_value()


def issue_access_token(subject: str, client_id: str, scopes: list[str]) -> tuple[str, int]:
    """Sign a new access token. Returns (token, expires_at as a Unix timestamp)."""
    now = int(time.time())
    expires_at = now + ACCESS_TOKEN_LIFETIME_SECONDS
    claims = {
        "iss": settings.oauth_issuer_url,
        "aud": settings.mcp_resource_url,
        "sub": subject,
        "client_id": client_id,
        "scope": " ".join(scopes),
        "iat": now,
        "exp": expires_at,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(claims, _key(), algorithm=_ALGORITHM), expires_at


def verify_access_token(token: str) -> AccessToken | None:
    """Return the token's details if it's valid for this server, else None.

    `algorithms` is pinned to HS256 so a token claiming another algorithm
    (including the classic `alg: none` forgery) is rejected outright.
    """
    try:
        claims = jwt.decode(
            token,
            _key(),
            algorithms=[_ALGORITHM],
            audience=settings.mcp_resource_url,
            issuer=settings.oauth_issuer_url,
            options={"require": _REQUIRED_CLAIMS},
        )
    except jwt.InvalidTokenError:
        return None

    return AccessToken(
        token=token,
        client_id=claims["client_id"],
        scopes=claims.get("scope", "").split(),
        expires_at=claims["exp"],
        resource=claims["aud"],
        subject=claims["sub"],
        claims=claims,
    )


def new_opaque_token() -> str:
    """A random, unguessable token (256 bits) for refresh tokens and auth codes."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """The SHA-256 fingerprint we store instead of the token itself.

    A fast hash is fine here (unlike passwords): the input is 256 random
    bits, so there's nothing to brute-force.
    """
    return hashlib.sha256(token.encode()).hexdigest()
