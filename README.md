# spotify-mcp

An MCP (Model Context Protocol) server for interacting with the Spotify Web API, built with Python and FastAPI. Runs locally — an MCP host (Claude Desktop, Claude Code, etc.) launches it as a subprocess on your own machine.

This is a portfolio project. The reasoning behind every architecture decision — and why — is logged in [`journal/`](journal/), one entry per decision, in the order they were made.

## How it works

[MCP](https://modelcontextprotocol.io/) is an open protocol that lets an AI client (like Claude) talk to external tools and data sources through a standard interface, instead of custom one-off integrations. A client connects to a server, and the server exposes **tools** the model can call — regular functions with a name, a description, and a typed schema, generated from the function's signature and docstring.

This project is two small, single-purpose local programs:

- **The MCP server itself** (`spotify_mcp.stdio_server`), talking to its host over **stdio** — the host process launches it and communicates over stdin/stdout, no network involved. This is what an MCP-compatible client actually connects to.
- **A local login helper** (`spotify_mcp.main`, a small FastAPI app), run separately, that handles the Spotify OAuth2 (Authorization Code + PKCE) flow at `/auth/login` and `/auth/callback`. Spotify data (like "what's currently playing") is user-specific, so a logged-in user's access token is needed to call the Spotify API on their behalf. The login step needs a browser and an HTTP redirect regardless of how the MCP server itself talks to its host — that's a property of OAuth, not of MCP transport — so it's kept as its own small process rather than folded into the stdio one.

Once logged in, the access/refresh token pair is stored in a small SQLite database, shared by both processes, and transparently refreshed when it's close to expiring.

```mermaid
graph TD
    Host["MCP Host<br/>(e.g. Claude Desktop / Claude Code)"]
    Browser["User's Browser"]

    subgraph Stdio["MCP server process (stdio)"]
        MCPServer["mcp_server.run()<br/>stdio transport"]
        Tools["MCP tools<br/>search, now_playing, top_tracks, ..."]
    end

    subgraph LoginApp["Login helper (FastAPI, run separately)"]
        AuthRoutes["/auth/login, /auth/callback<br/>(OAuth2 + PKCE)"]
    end

    SpotifyClient["Spotify client (httpx)"]
    DB[("SQLite<br/>spotify_mcp.db")]
    SpotifyAPI["api.spotify.com"]
    SpotifyAuth["accounts.spotify.com"]

    Host -->|"spawns as subprocess, stdin/stdout"| MCPServer
    MCPServer --> Tools
    Tools --> SpotifyClient

    Browser --> AuthRoutes
    AuthRoutes -->|"redirect + code"| SpotifyAuth
    SpotifyAuth -->|"redirect back"| AuthRoutes
    AuthRoutes -->|"store token"| DB

    SpotifyClient -->|"read / refresh token"| DB
    SpotifyClient -->|"Authorization: Bearer access_token"| SpotifyAPI
```

### Available tools

| Tool | Description |
|---|---|
| `ping` | Health check — confirms the MCP server is reachable. |
| `search_track` | Search Spotify's catalog for tracks matching a query. |
| `now_playing` | Get the track currently playing on the logged-in user's account, if any. |
| `top_tracks` | Get the user's most-listened-to tracks (short/medium/long term). |
| `top_artists` | Get the user's most-listened-to artists (short/medium/long term). |
| `recently_played` | Get the user's most recently played tracks. |
| `list_user_playlists` | List the logged-in user's playlists. |
| `playlist_tracks` | List the tracks in a playlist. |
| `create_user_playlist` | Create a new playlist. |
| `add_tracks` | Add one or more tracks to a playlist. |
| `pause` | Pause playback on the active device. |
| `resume` | Resume/start playback on the active device. |
| `skip_next` | Skip to the next track. |
| `skip_previous` | Skip to the previous track. |
| `set_playback_volume` | Set playback volume (0-100). |
| `queue_track` | Add a track to the playback queue. |

## Setup

**Prerequisites:**
- Python 3.14+
- [uv](https://github.com/astral-sh/uv) for dependency management
- A Spotify account and a [Spotify Developer app](https://developer.spotify.com/dashboard) (free to create)

**1. Install dependencies**

```bash
uv sync
```

**2. Create a Spotify Developer app**

At the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard):
- Create an app (any name/description).
- Add `http://127.0.0.1:8000/auth/callback` as a Redirect URI.
- Under "Which API/SDKs are you planning to use?", check **Web API**.
- Copy the app's **Client ID** (no client secret needed — this project uses PKCE).

**3. Configure environment variables**

```bash
cp .env.example .env
```

Fill in `SPOTIFY_CLIENT_ID` in `.env` with the Client ID from step 2. The other defaults work for local development as-is.

**4. Log in to Spotify**

Run the login helper:

```bash
uv run uvicorn spotify_mcp.main:app --port 8000
```

Open `http://127.0.0.1:8000/auth/login` in a browser and approve access. This only needs to be done once (until the refresh token is revoked) — the token is stored in `spotify_mcp.db`, which the MCP server reads from directly. The login helper doesn't need to stay running once you're logged in; stop it with Ctrl+C.

**5. Point your MCP host at the server**

Configure your MCP-compatible host (Claude Desktop, Claude Code, etc.) to launch the server. The exact config file differs per host, but the shape is the same everywhere — for example:

```json
{
  "mcpServers": {
    "spotify-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/spotify-mcp", "spotify-mcp"]
    }
  }
}
```

The host will spawn `uv run spotify-mcp` as a subprocess and talk to it over stdio.

## Testing

```bash
uv run pytest
```

Tests run against an isolated, throwaway SQLite database and mocked Spotify API responses — they never touch a real Spotify account or the local `spotify_mcp.db`. See [journal entry 11](journal/11-test-suite.md) for details.
