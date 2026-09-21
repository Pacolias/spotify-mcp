from contextlib import asynccontextmanager

from fastapi import FastAPI

from spotify_mcp.config import settings
from spotify_mcp.db.session import init_db
from spotify_mcp.mcp.server import mcp_server
from spotify_mcp.spotify.auth import router as auth_router

mcp_asgi_app = mcp_server.streamable_http_app()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # The MCP session manager runs its own task group for streamable HTTP
    # sessions. FastAPI's `app.mount()` does not forward lifespan events to
    # sub-apps, so it has to be started explicitly here, or every MCP request
    # fails with "Task group is not initialized".
    async with mcp_server.session_manager.run():
        yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(auth_router)
app.mount("/mcp-server", mcp_asgi_app)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
