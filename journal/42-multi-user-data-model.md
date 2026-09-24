# Multi-user data model for the remote MCP server

**Date:** 2026-09-24

Moving to a remote MCP server with our own authorization server ([entry 40](40-remote-mcp-no-monetization.md), [entry 41](41-mcp-authorization-server-via-sdk.md)) means the database has to serve up to 5 users and remember state across the separate HTTP requests of the OAuth flow. Today it's single-user: `SpotifyToken` is one row fixed at `id=1`.

Each decision below was made by the user after reviewing the options and their trade-offs.

## 1. User identity: the Spotify user ID as primary key

**Options:**
- **A. Spotify user ID** (the `id` returned by Spotify's `/me` endpoint) as the users table's primary key.
- **B. Our own ID** (integer or UUID), with the Spotify ID stored as a separate column. This would decouple the schema from Spotify and allow other login methods later, at the cost of an extra column and lookup step.

**Decision: A.** The Spotify user ID is always needed anyway: Spotify login is the only way in, and every user necessarily has a Spotify account. Trade-off accepted: the schema is tied to Spotify, so adding a different login method later would mean changing it.

Note: Spotify's `id` is stable and unique. It is not the same as `display_name`, which the user can change.

## 2. Access token format: JWT

The access token is what the MCP host sends with every request (`Authorization: Bearer ...`). The server uses it to check that the request is valid and to find out which user it belongs to.

**Options:**
- **A. Opaque random token**, looked up in the database on every request. Revocation is instant (delete the row), but every verification depends on the database. Used by e.g. GitHub, Stripe and Google's OAuth access tokens.
- **B. JWT**: a signed token that carries its claims inside (`sub`, `exp`...) and is verified by checking the signature, with no database lookup. It's the norm for identity providers (Auth0, Okta, Entra ID, Cognito, Keycloak; RFC 9068) and microservices. Downsides: it's hard to revoke before it expires, the signing key has to be protected (a leaked key lets an attacker forge tokens for any user), and its payload is readable by anyone, so it must never contain secrets.

**Decision: B (JWT).** Reason: it's the dominant format in industry, a classic interview topic, and it shows familiarity with signatures, claims and key management.

**Trade-off accepted, stated honestly:** JWT's main technical advantage (verifying without a database, across many servers) doesn't pay off at this project's scale. There are 5 users and one server, and every tool call reads the user's Spotify tokens from the database anyway. The choice is driven by learning and portfolio value, not by a scaling need. Revocation has to be handled explicitly (see the sub-decisions below).

**Sub-decisions still open:** signing algorithm (symmetric, e.g. HS256, vs. asymmetric, e.g. RS256/ES256), access token lifetime, revocation strategy, where the signing key lives, and which JWT library to use.
