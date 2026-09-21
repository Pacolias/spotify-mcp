# Spotify OAuth2 PKCE flow implemented

**Date:** 2026-09-21

`/auth/login` and `/auth/callback` (in `src/spotify_mcp/spotify/auth.py`) implement the Authorization Code + PKCE flow decided earlier. Notes on the implementation:

- The initial OAuth scope is minimal: `user-read-currently-playing` only, needed for the first two tools (search, currently-playing — search itself needs no scope, any valid user token works for it). More scopes get added as more tools are built, following least privilege.
- The `state` parameter (CSRF protection, standard OAuth2) is mapped to its PKCE `code_verifier` in an **in-memory dict**, for the short window between redirect and callback. This is only safe because the app is single-user and single-process; a multi-worker deployment would need a shared store (DB/Redis) instead. Flagged here as a known simplification, not an oversight.
- Tokens are stored as a single fixed row (`id=1`) in the `spotifytoken` SQLite table via `session.merge()` (upsert by primary key) — consistent with the single-user design.
- `get_valid_access_token()` is the one function every Spotify-calling tool will use: it returns a token from the DB, transparently refreshing it first if it's within 30 seconds of expiring. Raises a custom `NotAuthenticatedError` (not an HTTP exception) if no login has happened yet, since it's meant to be called from MCP tool code, not just FastAPI routes.

Verified with a live request that `/auth/login` builds a correctly-formed redirect to Spotify's `/authorize` endpoint with all required PKCE params. The full round trip (actually logging in through the browser and completing `/auth/callback`) needs a human in the loop — can't be automated from here. Confirmed working against a real Spotify account.

Bug found and fixed while testing: SQLite has no timezone-aware datetime type, so a tz-aware `expires_at` written on login came back **naive** on read, and Python refuses to compare a naive and an aware datetime (`TypeError`). Fixed by working in naive-but-UTC datetimes consistently everywhere in `auth.py`.
