"""The remote server end to end over HTTP: an MCP host connecting through
OAuth (with Spotify mocked) and then calling a tool on /mcp with its token."""

import json
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest
import respx
from fastapi.testclient import TestClient
from mcp.server.auth.middleware.auth_context import auth_context_var

from spotify_mcp.config import settings
from spotify_mcp.main import create_app
from spotify_mcp.oauth.tokens import issue_access_token
from spotify_mcp.spotify import auth as spotify_auth
from spotify_mcp.spotify.auth import generate_code_challenge, generate_code_verifier
from spotify_mcp.spotify.client import SPOTIFY_API_BASE

CLIENT_REDIRECT_URI = "http://localhost:9999/callback"
MCP_HEADERS = {"Accept": "application/json, text/event-stream"}


@pytest.fixture
def client(db_engine):
    # No ambient test user: the identity must come from the HTTP request.
    auth_context_var.set(None)
    with TestClient(
        create_app(), base_url=settings.oauth_issuer_url, follow_redirects=False
    ) as test_client:
        yield test_client


def _query(url: str) -> dict[str, str]:
    return {key: values[0] for key, values in parse_qs(urlparse(url).query).items()}


def _rpc(client: TestClient, token: str, method: str, params: dict[str, object]) -> httpx.Response:
    return client.post(
        "/mcp",
        headers={**MCP_HEADERS, "Authorization": f"Bearer {token}"},
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
    )


def _result(response: httpx.Response) -> dict[str, object]:
    """The JSON-RPC result from a streamable HTTP response (an SSE stream)."""
    assert response.status_code == 200, response.text
    data = next(line for line in response.text.splitlines() if line.startswith("data: "))
    return json.loads(data.removeprefix("data: "))["result"]


def _connect(client: TestClient) -> str:
    """Do what an MCP host does when the user clicks "connect", with Spotify
    mocked. Returns the access token the host ends up with."""
    client_id = client.post(
        "/register",
        json={
            "redirect_uris": [CLIENT_REDIRECT_URI],
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
        },
    ).json()["client_id"]

    verifier = generate_code_verifier()
    to_spotify = client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": CLIENT_REDIRECT_URI,
            "code_challenge": generate_code_challenge(verifier),
            "code_challenge_method": "S256",
            "state": "host-state",
            "resource": settings.mcp_resource_url,
        },
    )
    spotify_state = _query(to_spotify.headers["location"])["state"]

    # The user approves on Spotify, which redirects back to our callback.
    respx.post(spotify_auth.SPOTIFY_TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "alice-spotify-token",
                "refresh_token": "alice-spotify-refresh",
                "expires_in": 3600,
                "scope": "user-read-currently-playing",
            },
        )
    )
    respx.get(spotify_auth.SPOTIFY_ME_URL).mock(
        return_value=httpx.Response(200, json={"id": "alice", "display_name": "Alice"})
    )
    back_to_host = client.get("/auth/callback", params={"code": "c", "state": spotify_state})
    assert back_to_host.status_code == 302
    assert back_to_host.headers["location"].startswith(CLIENT_REDIRECT_URI)
    code = _query(back_to_host.headers["location"])["code"]

    tokens = client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "redirect_uri": CLIENT_REDIRECT_URI,
            "code_verifier": verifier,
        },
    ).json()
    return str(tokens["access_token"])


def test_mcp_without_a_token_points_the_host_to_oauth(client) -> None:
    response = client.post("/mcp", headers=MCP_HEADERS, json={"jsonrpc": "2.0", "id": 1})

    assert response.status_code == 401
    assert "/.well-known/oauth-protected-resource/mcp" in response.headers["www-authenticate"]


def test_metadata_names_this_server_as_its_own_authorization_server(client) -> None:
    resource = client.get("/.well-known/oauth-protected-resource/mcp").json()
    server = client.get("/.well-known/oauth-authorization-server").json()

    assert resource["resource"] == settings.mcp_resource_url
    assert resource["authorization_servers"] == [settings.oauth_issuer_url]
    # Must equal our tokens' `iss` exactly: no trailing slash added.
    assert server["issuer"] == settings.oauth_issuer_url


def test_token_for_another_audience_is_rejected(client) -> None:
    token, _ = issue_access_token("alice", "c1", [])
    claims = jwt.decode(token, options={"verify_signature": False})
    claims["aud"] = "https://elsewhere.example/mcp"
    forged = jwt.encode(claims, settings.jwt_signing_key.get_secret_value(), algorithm="HS256")

    response = _rpc(client, forged, "tools/call", {"name": "ping", "arguments": {}})

    assert response.status_code == 401


@respx.mock
def test_connected_host_calls_tools_as_the_user_who_logged_in(client) -> None:
    token = _connect(client)
    now_playing = respx.get(f"{SPOTIFY_API_BASE}/me/player/currently-playing").mock(
        return_value=httpx.Response(
            200,
            json={
                "is_playing": True,
                "item": {
                    "name": "Song",
                    "artists": [{"name": "Artist"}],
                    "album": {"name": "Album"},
                    "external_urls": {"spotify": "https://open.spotify.com/track/1"},
                },
            },
        )
    )

    _result(
        _rpc(
            client,
            token,
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test-host", "version": "1"},
            },
        )
    )
    result = _result(_rpc(client, token, "tools/call", {"name": "now_playing", "arguments": {}}))

    assert result["content"][0]["text"].startswith("Playing: Song")
    # The Spotify call carried *alice's* Spotify token, resolved from our JWT.
    assert now_playing.calls.last.request.headers["Authorization"] == "Bearer alice-spotify-token"


def test_callback_with_unknown_state_shows_an_error(client) -> None:
    response = client.get("/auth/callback", params={"code": "c", "state": "never-issued"})

    assert response.status_code == 400
    assert "Start connecting again" in response.json()["detail"]
