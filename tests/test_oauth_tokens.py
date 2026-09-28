import time

import jwt

from spotify_mcp.config import settings
from spotify_mcp.oauth.tokens import (
    ACCESS_TOKEN_LIFETIME_SECONDS,
    hash_token,
    issue_access_token,
    new_opaque_token,
    verify_access_token,
)

KEY = settings.jwt_signing_key.get_secret_value()


def _valid_claims(**overrides: object) -> dict[str, object]:
    now = int(time.time())
    claims: dict[str, object] = {
        "iss": settings.oauth_issuer_url,
        "aud": settings.mcp_resource_url,
        "sub": "spotify-user-1",
        "client_id": "client-1",
        "scope": "a b",
        "iat": now,
        "exp": now + 60,
    }
    claims.update(overrides)
    return claims


def test_issued_token_round_trips() -> None:
    token, expires_at = issue_access_token("spotify-user-1", "client-1", ["read", "write"])

    access = verify_access_token(token)

    assert access is not None
    assert access.subject == "spotify-user-1"
    assert access.client_id == "client-1"
    assert access.scopes == ["read", "write"]
    assert access.resource == settings.mcp_resource_url
    assert access.expires_at == expires_at
    assert expires_at - time.time() <= ACCESS_TOKEN_LIFETIME_SECONDS


def test_expired_token_is_rejected() -> None:
    past = int(time.time()) - 120
    token = jwt.encode(_valid_claims(iat=past - 60, exp=past), KEY, algorithm="HS256")

    assert verify_access_token(token) is None


def test_token_signed_with_another_key_is_rejected() -> None:
    token = jwt.encode(_valid_claims(), "some-other-key-that-is-32-bytes-long!!", algorithm="HS256")

    assert verify_access_token(token) is None


def test_tampered_payload_is_rejected() -> None:
    token, _ = issue_access_token("spotify-user-1", "client-1", [])
    header, _payload, signature = token.split(".")
    forged_payload = jwt.encode(_valid_claims(sub="someone-else"), KEY, algorithm="HS256").split(
        "."
    )[1]

    assert verify_access_token(f"{header}.{forged_payload}.{signature}") is None


def test_token_for_another_audience_is_rejected() -> None:
    token = jwt.encode(
        _valid_claims(aud="https://other-server.example/mcp"), KEY, algorithm="HS256"
    )

    assert verify_access_token(token) is None


def test_token_from_another_issuer_is_rejected() -> None:
    token = jwt.encode(_valid_claims(iss="https://evil.example"), KEY, algorithm="HS256")

    assert verify_access_token(token) is None


def test_unsigned_alg_none_token_is_rejected() -> None:
    token = jwt.encode(_valid_claims(), None, algorithm="none")

    assert verify_access_token(token) is None


def test_token_missing_a_required_claim_is_rejected() -> None:
    claims = _valid_claims()
    del claims["client_id"]
    token = jwt.encode(claims, KEY, algorithm="HS256")

    assert verify_access_token(token) is None


def test_garbage_is_rejected() -> None:
    assert verify_access_token("not-a-jwt") is None


def test_opaque_tokens_are_unique_and_long() -> None:
    tokens = {new_opaque_token() for _ in range(100)}

    assert len(tokens) == 100
    assert all(len(t) >= 43 for t in tokens)  # 32 random bytes, base64url


def test_hash_is_deterministic_and_hides_the_token() -> None:
    token = new_opaque_token()

    assert hash_token(token) == hash_token(token)
    assert hash_token(token) != token
    assert len(hash_token(token)) == 64
