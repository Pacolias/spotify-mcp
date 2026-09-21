import secrets

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class BearerTokenMiddleware:
    """Rejects any HTTP request to the wrapped ASGI app that doesn't carry
    `Authorization: Bearer <token>`. Guards the MCP endpoint specifically —
    it's network-reachable now that the transport is HTTP, unlike the
    /auth/* routes, which are reached by a browser redirect and are already
    gated by Spotify's own login."""

    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope["headers"])
        provided = headers.get(b"authorization", b"").decode()

        if not secrets.compare_digest(provided, f"Bearer {self.token}"):
            response = JSONResponse({"detail": "Unauthorized"}, status_code=401)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
