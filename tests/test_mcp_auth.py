from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from spotify_mcp.mcp.auth import BearerTokenMiddleware


def _protected_test_app(token: str) -> BearerTokenMiddleware:
    # A minimal standalone app, not the real spotify_mcp.main.app — the real
    # app's MCP session manager is a module-level singleton whose .run() can
    # only be entered once per process, so multiple TestClient(app) calls
    # across tests would conflict. Testing the middleware in isolation avoids
    # that entirely and is all this behavior actually depends on.
    async def ok(request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    inner = Starlette(routes=[Route("/ping", ok)])
    return BearerTokenMiddleware(inner, token=token)


def test_rejects_missing_bearer_token() -> None:
    client = TestClient(_protected_test_app("secret"))

    response = client.get("/ping")

    assert response.status_code == 401


def test_rejects_wrong_bearer_token() -> None:
    client = TestClient(_protected_test_app("secret"))

    response = client.get("/ping", headers={"Authorization": "Bearer wrong"})

    assert response.status_code == 401


def test_accepts_correct_bearer_token() -> None:
    client = TestClient(_protected_test_app("secret"))

    response = client.get("/ping", headers={"Authorization": "Bearer secret"})

    assert response.status_code == 200
    assert response.text == "ok"
