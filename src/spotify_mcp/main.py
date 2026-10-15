"""The HTTP server: FastAPI as the main app, with the MCP SDK's app (the
/mcp endpoint plus the OAuth routes and metadata) mounted inside it
(journal 46, decision 1)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, Response
from mcp.server.transport_security import TransportSecuritySettings

from spotify_mcp.config import settings
from spotify_mcp.db.session import init_db
from spotify_mcp.mcp.server import mcp_server, oauth_provider
from spotify_mcp.oauth.provider import UnknownAuthorizationError
from spotify_mcp.spotify import auth as auth_module


def _transport_security() -> TransportSecuritySettings:
    # DNS rebinding protection: only accept requests addressed to our own
    # public host, so a malicious web page can't reach the server through a
    # domain that happens to resolve to it.
    url = urlparse(settings.mcp_resource_url)
    return TransportSecuritySettings(
        allowed_hosts=[url.netloc], allowed_origins=[f"{url.scheme}://{url.netloc}"]
    )


async def spotify_callback(
    code: str | None = None, state: str | None = None, error: str | None = None
) -> Response:
    """Spotify redirects here after the user approves (or denies) access."""
    if not state:
        raise HTTPException(status_code=400, detail="Missing state")
    if auth_module.is_local_login(state):
        return await auth_module.finish_local_login(code, state, error)
    try:
        redirect_to = await oauth_provider.complete_authorization(state, code=code, error=error)
    except UnknownAuthorizationError:
        raise HTTPException(
            status_code=400,
            detail="Unknown or expired login attempt. Start connecting again from your MCP client.",
        ) from None
    return RedirectResponse(redirect_to, status_code=302)


def health() -> dict[str, str]:
    return {"status": "ok"}


def create_app() -> FastAPI:
    """Build a fresh app. A factory because the SDK's session manager can
    only be started once, so each app (and each test) needs its own."""
    # Stateless: every request stands alone (journal 46, decision 3).
    mcp_app = mcp_server.streamable_http_app(
        stateless_http=True, transport_security=_transport_security()
    )
    session_manager = mcp_server.session_manager

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        init_db()
        # FastAPI doesn't pass lifespan events to mounted apps, so the SDK's
        # session manager has to be started here (journal 08).
        async with session_manager.run():
            yield

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(auth_module.router)
    app.add_api_route("/auth/callback", spotify_callback, methods=["GET"])
    app.add_api_route("/health", health, methods=["GET"])
    # Last, so FastAPI's own routes match first.
    app.mount("/", mcp_app)
    return app


app = create_app()
