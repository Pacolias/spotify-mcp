# Streamable HTTP transport implemented, and the first real connection from Claude Code

**Date:** 2026-10-15

Implements [entry 45](45-remote-only-drop-stdio-and-login.md) (remote only) and the three decisions of [entry 46](46-http-transport-design.md).

## What changed

- **`spotify-mcp serve`** runs a FastAPI app with the SDK's app mounted at `/`. It serves `/mcp` (stateless streamable HTTP; requests without a valid token get a `401` pointing at the OAuth metadata), the SDK's OAuth endpoints and `.well-known` metadata, `/auth/callback` (Spotify's redirect, handled by the provider from [entry 44](44-oauth-provider-implemented.md)) and `/health`.
- **Explicit `user_id`.** Every Spotify client function takes the user as its first argument. Tools resolve it once with `current_user_id()`, which reads the `sub` of the verified access token.
- **Removed:** the stdio entrypoint, `spotify-mcp login`, and the single-user shortcuts (`user_id=None` meaning "the only stored user", in-memory pending logins).
- **The app is built by a factory, `create_app()`.** The SDK's session manager can only be started once per instance, so every app, and every test, needs a fresh one.

## Verified end to end

Claude Code was registered with `claude mcp add --transport http`, and **Authenticate** in `/mcp` went through the whole flow against the real Spotify: `POST /register` → `GET /authorize` → Spotify consent → `GET /auth/callback` → `POST /token` → `POST /mcp`. `now_playing` then returned the track actually playing. After a server restart the tools kept working without signing in again: sessions are stateless, and the JWT is still valid.

`tests/test_http_server.py` covers the same flow over HTTP with Spotify mocked, and checks that the Spotify call carries the token of the user who logged in.

## Implementation details (decided by Claude, per the working agreement)

- **DNS rebinding protection.** `/mcp` only accepts requests whose `Host` (and `Origin`, if present) is the server's own public host, taken from `MCP_RESOURCE_URL`.
- **Exact issuer.** Building the SDK's settings from a bare `AnyHttpUrl` appended a `/` to the issuer (`http://127.0.0.1:8000/`), which no longer matched our tokens' `iss`. RFC 8414 requires an exact match, so the settings are now built in a way that keeps the URL as written. A test pins it.
- **`validate_token_resource` on.** The SDK also checks that a token was issued for this server, on top of the `aud` check in `verify_access_token`.
- **No secrets in the access log.** uvicorn logged full URLs, so Spotify's authorization code and the PKCE/state values ended up on disk. The access log now records paths only. Found by reading the log of the first real connection.
- **Tests run as an authenticated test user.** An autouse fixture sets the SDK's auth context. Before this, tool tests silently fell back to whatever user was in the developer's local database.

## Gotcha found on the way

Claude Code reads its MCP server config when a session starts. Re-registering the server from inside a running session isn't picked up by that session's `/mcp` menu, so it kept showing the old, broken stdio server until Claude Code was restarted.

## Still open

Hosting, the production database (SQLite vs Postgres, migrations), rate limits, and Docker/CI-CD for deployment.
