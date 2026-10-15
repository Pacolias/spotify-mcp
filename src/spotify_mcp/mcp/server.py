from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from mcp.server.mcpserver import MCPServer

from spotify_mcp.config import settings
from spotify_mcp.oauth.provider import SpotifyOAuthProvider

oauth_provider = SpotifyOAuthProvider()

# This server is both the MCP resource server and the OAuth authorization
# server that MCP hosts connect through (journal 41). The SDK serves the OAuth
# endpoints and metadata, and rejects /mcp requests without a valid token.
mcp_server = MCPServer(
    "spotify-mcp",
    auth_server_provider=oauth_provider,
    # model_validate rather than AnyHttpUrl(...): AuthSettings keeps a
    # path-less issuer exactly as written, while a bare AnyHttpUrl appends "/",
    # and the issuer has to match our tokens' `iss` character for character.
    auth=AuthSettings.model_validate(
        {
            "issuer_url": settings.oauth_issuer_url,
            "resource_server_url": settings.mcp_resource_url,
            "client_registration_options": ClientRegistrationOptions(enabled=True),
            "revocation_options": RevocationOptions(enabled=True),
            # Belt and braces: verify_access_token already checks `aud`.
            "validate_token_resource": True,
        }
    ),
)


@mcp_server.tool()
def ping() -> str:
    """Health-check tool: confirms the MCP server is reachable and tools can be called."""
    return "pong"


# Importing these registers their @mcp_server.tool()/@mcp_server.resource()/
# @mcp_server.prompt()-decorated functions above. Must stay at the bottom:
# each module imports `mcp_server` from this file, so it needs to already
# be defined first.
from spotify_mcp.mcp import prompts, resources  # noqa: E402, F401
from spotify_mcp.mcp.tools import (  # noqa: E402, F401
    library,
    personal,
    playback,
    playlists,
    search,
    youtube,
)
