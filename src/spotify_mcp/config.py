from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "spotify-mcp"

    spotify_client_id: str
    spotify_redirect_uri: str = "http://127.0.0.1:8000/auth/callback"
    # Space-separated OAuth scopes. Starts minimal (principle of least
    # privilege) and grows as we add tools that need more Spotify permissions.
    spotify_scopes: str = "user-read-currently-playing"

    database_url: str = "sqlite:///./spotify_mcp.db"

    # Required bearer token for calling the MCP endpoint (/mcp-server/*),
    # since it's reachable over the network now that the transport is HTTP.
    mcp_bearer_token: str


settings = Settings()
