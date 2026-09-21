from contextlib import asynccontextmanager

from fastapi import FastAPI

from spotify_mcp.config import settings
from spotify_mcp.db.session import init_db
from spotify_mcp.spotify.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(auth_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
