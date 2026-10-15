"""The MCP authorization server, driven through the SDK's real OAuth routes
(/register, /authorize, /token, /revoke) with Spotify mocked out."""

import asyncio
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx
from mcp.server.auth.routes import create_auth_routes
from mcp.server.auth.settings import ClientRegistrationOptions, RevocationOptions
from pydantic import AnyHttpUrl
from sqlmodel import Session, select
from starlette.applications import Starlette
from starlette.testclient import TestClient

from spotify_mcp.config import settings
from spotify_mcp.db import models
from spotify_mcp.oauth.provider import SpotifyOAuthProvider, UnknownAuthorizationError
from spotify_mcp.oauth.tokens import hash_token, verify_access_token
from spotify_mcp.spotify import auth as spotify_auth
from spotify_mcp.spotify.auth import _utcnow, generate_code_challenge, generate_code_verifier

CLIENT_REDIRECT_URI = "http://localhost:9999/callback"


@pytest.fixture
def provider(db_engine) -> SpotifyOAuthProvider:
    return SpotifyOAuthProvider()


@pytest.fixture
def client(provider) -> TestClient:
    routes = create_auth_routes(
        provider,
        issuer_url=AnyHttpUrl(settings.oauth_issuer_url),
        client_registration_options=ClientRegistrationOptions(enabled=True),
        revocation_options=RevocationOptions(enabled=True),
    )
    return TestClient(Starlette(routes=routes), follow_redirects=False)


@pytest.fixture
def spotify():
    """Spotify's token and /me endpoints, as seen by a successful login."""
    with respx.mock(assert_all_called=False) as mock:
        mock.post(spotify_auth.SPOTIFY_TOKEN_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "spotify-at",
                    "refresh_token": "spotify-rt",
                    "expires_in": 3600,
                    "scope": "user-read-currently-playing",
                },
            )
        )
        mock.get(spotify_auth.SPOTIFY_ME_URL).mock(
            return_value=httpx.Response(200, json={"id": "alice", "display_name": "Alice"})
        )
        yield mock


def _register(client: TestClient) -> str:
    response = client.post(
        "/register",
        json={
            "redirect_uris": [CLIENT_REDIRECT_URI],
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "client_name": "Test MCP host",
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["client_id"])


def _authorize(client: TestClient, client_id: str, code_verifier: str, **extra: str) -> str:
    """Hit /authorize; returns the Location it redirects to."""
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": CLIENT_REDIRECT_URI,
        "code_challenge": generate_code_challenge(code_verifier),
        "code_challenge_method": "S256",
        "state": "client-state",
        "resource": settings.mcp_resource_url,
        **extra,
    }
    response = client.get("/authorize", params=params)
    assert response.status_code == 302, response.text
    return str(response.headers["location"])


def _query(url: str) -> dict[str, str]:
    return {key: values[0] for key, values in parse_qs(urlparse(url).query).items()}


def _log_in(client: TestClient, provider: SpotifyOAuthProvider) -> tuple[str, str, str]:
    """Register, authorize and come back from Spotify. Returns (client_id,
    our authorization code, the PKCE verifier)."""
    client_id = _register(client)
    code_verifier = generate_code_verifier()
    spotify_url = _authorize(client, client_id, code_verifier)
    state = _query(spotify_url)["state"]

    back = asyncio.run(provider.complete_authorization(state, code="spotify-code"))

    assert back.startswith(CLIENT_REDIRECT_URI)
    query = _query(back)
    assert query["state"] == "client-state"
    return client_id, query["code"], code_verifier


def _exchange_code(client: TestClient, client_id: str, code: str, verifier: str) -> httpx.Response:
    return client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "redirect_uri": CLIENT_REDIRECT_URI,
            "code_verifier": verifier,
        },
    )


def _refresh(client: TestClient, client_id: str, refresh_token: str) -> httpx.Response:
    return client.post(
        "/token",
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": refresh_token,
        },
    )


def test_authorize_sends_the_user_to_spotify_login(client, provider) -> None:
    client_id = _register(client)

    location = _authorize(client, client_id, generate_code_verifier())

    assert location.startswith(spotify_auth.SPOTIFY_AUTHORIZE_URL)
    assert _query(location)["code_challenge_method"] == "S256"


def test_full_flow_issues_tokens_for_the_spotify_user(client, provider, spotify, db_engine) -> None:
    client_id, code, verifier = _log_in(client, provider)

    response = _exchange_code(client, client_id, code, verifier)

    assert response.status_code == 200, response.text
    body = response.json()
    access = verify_access_token(body["access_token"])
    assert access is not None
    assert access.subject == "alice"
    assert access.client_id == client_id
    assert body["refresh_token"]
    with Session(db_engine) as session:
        assert session.get(models.SpotifyCredentials, "alice") is not None


def test_codes_and_refresh_tokens_are_stored_only_as_hashes(
    client, provider, spotify, db_engine
) -> None:
    client_id, code, verifier = _log_in(client, provider)
    with Session(db_engine) as session:
        assert session.get(models.AuthorizationCode, hash_token(code)) is not None

    refresh_token = _exchange_code(client, client_id, code, verifier).json()["refresh_token"]

    with Session(db_engine) as session:
        assert session.get(models.RefreshToken, hash_token(refresh_token)) is not None
        assert session.get(models.RefreshToken, refresh_token) is None


def test_authorization_code_is_single_use(client, provider, spotify) -> None:
    client_id, code, verifier = _log_in(client, provider)
    assert _exchange_code(client, client_id, code, verifier).status_code == 200

    second = _exchange_code(client, client_id, code, verifier)

    assert second.status_code == 400
    assert second.json()["error"] == "invalid_grant"


def test_wrong_pkce_verifier_is_rejected(client, provider, spotify) -> None:
    client_id, code, _ = _log_in(client, provider)

    response = _exchange_code(client, client_id, code, generate_code_verifier())

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_grant"


def test_refresh_rotates_the_refresh_token(client, provider, spotify) -> None:
    client_id, code, verifier = _log_in(client, provider)
    first = _exchange_code(client, client_id, code, verifier).json()

    response = _refresh(client, client_id, first["refresh_token"])

    assert response.status_code == 200, response.text
    second = response.json()
    assert second["refresh_token"] != first["refresh_token"]
    access = verify_access_token(second["access_token"])
    assert access is not None and access.subject == "alice"


def test_reusing_a_rotated_refresh_token_revokes_the_whole_grant(client, provider, spotify) -> None:
    client_id, code, verifier = _log_in(client, provider)
    stolen = _exchange_code(client, client_id, code, verifier).json()["refresh_token"]
    current = _refresh(client, client_id, stolen).json()["refresh_token"]

    replay = _refresh(client, client_id, stolen)

    assert replay.status_code == 400
    # The legitimate client's newer token is gone too.
    assert _refresh(client, client_id, current).status_code == 400


def _revoke(client: TestClient, client_id: str, token: str) -> httpx.Response:
    # The SDK's RevocationRequest requires a client_secret field even for
    # public clients (no secret), so an empty one is sent.
    return client.post(
        "/revoke", data={"client_id": client_id, "client_secret": "", "token": token}
    )


def test_revoking_a_refresh_token_stops_refreshes(client, provider, spotify) -> None:
    client_id, code, verifier = _log_in(client, provider)
    refresh_token = _exchange_code(client, client_id, code, verifier).json()["refresh_token"]

    response = _revoke(client, client_id, refresh_token)

    assert response.status_code == 200
    assert _refresh(client, client_id, refresh_token).status_code == 400


def test_revoking_an_access_token_revokes_the_refresh_token(client, provider, spotify) -> None:
    client_id, code, verifier = _log_in(client, provider)
    tokens = _exchange_code(client, client_id, code, verifier).json()

    assert _revoke(client, client_id, tokens["access_token"]).status_code == 200

    assert _refresh(client, client_id, tokens["refresh_token"]).status_code == 400


def test_user_cancelling_on_spotify_returns_access_denied_to_the_client(client, provider) -> None:
    client_id = _register(client)
    state = _query(_authorize(client, client_id, generate_code_verifier()))["state"]

    back = asyncio.run(provider.complete_authorization(state, error="access_denied"))

    query = _query(back)
    assert back.startswith(CLIENT_REDIRECT_URI)
    assert query["error"] == "access_denied"
    assert query["state"] == "client-state"
    assert "code" not in query


def test_spotify_failure_returns_server_error_to_the_client(client, provider) -> None:
    client_id = _register(client)
    state = _query(_authorize(client, client_id, generate_code_verifier()))["state"]

    with respx.mock:
        respx.post(spotify_auth.SPOTIFY_TOKEN_URL).mock(return_value=httpx.Response(500))
        back = asyncio.run(provider.complete_authorization(state, code="spotify-code"))

    assert _query(back)["error"] == "server_error"


def test_unknown_state_is_rejected(provider) -> None:
    with pytest.raises(UnknownAuthorizationError):
        asyncio.run(provider.complete_authorization("never-issued", code="spotify-code"))


def test_spotify_callback_state_is_single_use(client, provider, spotify) -> None:
    client_id = _register(client)
    state = _query(_authorize(client, client_id, generate_code_verifier()))["state"]
    asyncio.run(provider.complete_authorization(state, code="spotify-code"))

    with pytest.raises(UnknownAuthorizationError):
        asyncio.run(provider.complete_authorization(state, code="spotify-code"))


def test_expired_pending_authorization_is_rejected(client, provider, db_engine) -> None:
    client_id = _register(client)
    state = _query(_authorize(client, client_id, generate_code_verifier()))["state"]
    with Session(db_engine) as session:
        pending = session.get(models.PendingAuthorization, state)
        assert pending is not None
        pending.expires_at = _utcnow() - timedelta(seconds=1)
        session.add(pending)
        session.commit()

    with pytest.raises(UnknownAuthorizationError):
        asyncio.run(provider.complete_authorization(state, code="spotify-code"))


def test_tokens_for_another_resource_are_refused(client, provider) -> None:
    client_id = _register(client)

    location = _authorize(
        client, client_id, generate_code_verifier(), resource="https://elsewhere.example/mcp"
    )

    assert location.startswith(CLIENT_REDIRECT_URI)
    assert _query(location)["error"] == "invalid_target"


def test_expired_rows_are_purged_on_the_next_authorization(client, provider, db_engine) -> None:
    client_id = _register(client)
    old_state = _query(_authorize(client, client_id, generate_code_verifier()))["state"]
    with Session(db_engine) as session:
        pending = session.get(models.PendingAuthorization, old_state)
        assert pending is not None
        pending.expires_at = _utcnow() - timedelta(seconds=1)
        session.add(pending)
        session.commit()

    _authorize(client, client_id, generate_code_verifier())

    with Session(db_engine) as session:
        states = session.exec(select(models.PendingAuthorization.state)).all()
    assert old_state not in states
    assert len(states) == 1
