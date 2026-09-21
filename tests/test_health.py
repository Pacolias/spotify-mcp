from fastapi.testclient import TestClient

from spotify_mcp.main import app


def test_health_endpoint(db_engine) -> None:
    # Entering TestClient as a context manager runs the app's lifespan
    # (init_db + MCP session manager startup), so db_engine has to be
    # patched in beforehand to avoid touching the real spotify_mcp.db.
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
