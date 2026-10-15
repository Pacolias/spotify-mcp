# OAuth authorization server implemented: tables and provider

**Date:** 2026-10-15

Implements decisions 2–4 and items 6–8 of [entry 42](42-multi-user-data-model.md), on top of the SDK interface chosen in [entry 41](41-mcp-authorization-server-via-sdk.md).

## What changed

- **Four tables:** `oauth_clients` (registered MCP hosts, SDK metadata as one JSON column), `pending_authorizations` (the host's request while the user is on Spotify's consent screen, 10 min), `authorization_codes` (hashed, 5 min, single use) and `refresh_tokens` (hashed, 30 days, rotated on every use).
- **`SpotifyOAuthProvider`** (`spotify_mcp/oauth/provider.py`) implements the SDK's `OAuthAuthorizationServerProvider`. The SDK serves `/register`, `/authorize`, `/token` and `/revoke` and validates PKCE, redirect URIs and expiry; the provider stores state and talks to Spotify.
- The flow: `/authorize` parks the host's request and redirects to Spotify. Spotify sends the user back to `complete_authorization()`, which finishes the Spotify login, creates our authorization code and redirects to the host. The host then exchanges the code at `/token` for a JWT access token and a refresh token.
- **Refactor:** the Spotify login steps (code exchange, `/me`, encrypted storage) moved out of the local callback into `complete_login()`, shared by the `login` command and the provider.

## Implementation details (decided by Claude, per the working agreement)

- **Refresh token reuse detection.** A rotated refresh token isn't deleted; it's marked `rotated_at`. If it's ever presented again, someone else has a copy, so every refresh token for that user and client is revoked. OAuth 2.1 recommends this for public clients such as MCP hosts.
- **Revocation** with either token deletes the user's refresh tokens for that client. An access token (JWT) keeps working until it expires, at most an hour, as decided in entry 42 (2c).
- **Resource check.** `/authorize` rejects a `resource` other than our own MCP endpoint (`invalid_target`, RFC 8707), so a token can't be requested for a different server.
- **Errors go back to the host.** If the user cancels on Spotify the host gets `access_denied`; if Spotify fails, `server_error`. An unknown or expired `state` can't be redirected anywhere, so it raises `UnknownAuthorizationError` for the callback route to show an error page.
- **Housekeeping.** Expired pending authorizations, codes and refresh tokens are purged on each new authorization, so the tables don't grow forever.
- **Client secrets are stored as issued**, not hashed: the SDK's client authentication compares the presented secret with what `get_client()` returns.
- **Dynamic client registration is open to anyone.** It's how MCP hosts get a `client_id`, and the only registration mechanism the SDK implements server-side. Who can actually log in is still limited by Spotify's 5-user allow-list.

## Testing

`tests/test_oauth_provider.py` drives the SDK's real OAuth routes with Spotify mocked: the full flow, single-use codes, wrong PKCE verifier, rotation, reuse detection, revocation, cancellation, Spotify failure, expired/unknown state, the resource check and purging.

Found along the way: the SDK's `/revoke` requires a `client_secret` form field even from public clients with no secret. The tests send an empty one. Worth checking against Claude once the server is live.

## Not done yet

The provider isn't mounted on an HTTP app, and there's no Spotify callback route for the remote flow. Both come with the streamable HTTP transport. That step also has to decide which URL Spotify redirects to, which is tied to the open question of what happens to the stdio entrypoint and the `login` command.
