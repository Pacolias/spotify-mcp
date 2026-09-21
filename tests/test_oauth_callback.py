import httpx
import respx
from fastapi.testclient import TestClient

from spotify_mcp.main import app
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

    with TestClient(app) as client:
        response = client.get("/auth/callback", params={"code": "abc", "state": "test-state"})

    assert response.status_code == 200
    assert "Logged in to Spotify" in response.text
    assert auth_module.login_complete.is_set()
