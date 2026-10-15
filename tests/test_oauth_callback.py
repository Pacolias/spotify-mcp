import httpx
import respx
from fastapi.testclient import TestClient
from sqlmodel import Session

from spotify_mcp.db.encryption import decrypt
from spotify_mcp.db.models import SpotifyCredentials, User
from spotify_mcp.main import create_app
from spotify_mcp.spotify import auth as auth_module


@respx.mock
def test_callback_shows_success_page_and_sets_login_complete(db_engine) -> None:
    auth_module._pending_logins["test-state"] = "test-verifier"
    auth_module.login_complete.clear()

    respx.post(auth_module.SPOTIFY_TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "at",
                "refresh_token": "rt",
                "expires_in": 3600,
                "scope": "user-read-currently-playing",
            },
        )
    )

    respx.get(auth_module.SPOTIFY_ME_URL).mock(
        return_value=httpx.Response(200, json={"id": "alice", "display_name": "Alice"})
    )

    with TestClient(create_app(), base_url="http://127.0.0.1:8000") as client:
        response = client.get("/auth/callback", params={"code": "abc", "state": "test-state"})

    assert response.status_code == 200
    assert "Logged in to Spotify" in response.text
    assert auth_module.login_complete.is_set()
    with Session(db_engine) as session:
        user = session.get(User, "alice")
        credentials = session.get(SpotifyCredentials, "alice")
    assert user is not None and user.display_name == "Alice"
    assert credentials is not None
    assert decrypt(credentials.encrypted_access_token) == "at"
    assert decrypt(credentials.encrypted_refresh_token) == "rt"
