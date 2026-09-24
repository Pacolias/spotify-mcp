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

**Sub-decisions still open:** where the signing key lives, and which JWT library to use.

### 2a. Signing algorithm: HS256 (symmetric)

**Options:**
- **A. Symmetric (HS256):** one secret key both signs and verifies. The simplest setup: a single random secret. The downside is that anyone able to verify can also forge, so the key could never be shared with another verifying service.
- **B. Asymmetric (RS256/ES256):** a private key signs, and a public key (usually published as a JWKS at `/.well-known/jwks.json`) verifies. It's what identity providers use, and it would have brought public-key crypto, JWKS and `kid`-based key rotation into the project, at the cost of a key pair to generate, store and configure.

**Decision: A (HS256).** In this project the issuer and the verifier are the same server, so no other party ever needs to verify our tokens. Trade-off accepted: asymmetric signing, JWKS and key rotation are left out of what the project demonstrates.

### 2b. Access token lifetime: about 1 hour

The MCP host also gets a refresh token and renews the access token automatically when it expires, so the lifetime affects security, not user experience.

**Options:**
- **A. Short (5–15 min):** a stolen token is only useful briefly, and revoking a user's refresh token is enough to cut them off within minutes, with no revocation list needed.
- **B. Medium (~1 hour):** a common industry value, with fewer refreshes.
- **C. Long (days):** almost no refreshes, but a stolen token lives for days, which in practice forces a revocation list checked on every request.

**Decision: B (~1 hour).** Trade-off accepted: a stolen or revoked access token keeps working for up to an hour, unless the revocation strategy (still open) adds an immediate cut-off.

### 2c. Revocation: no immediate cut-off for access tokens

Revoking means invalidating a token before it expires. Here that would happen when removing a user (e.g. to free one of the 5 slots), when the user disconnects the server from their MCP host (the SDK provides a `/revoke` endpoint), or if a token is suspected stolen.

**Options:**
- **A. No immediate cut-off:** revoking only invalidates the refresh token. The access token keeps working until it expires (at most ~1 hour, per 2b), and the next refresh then fails. Verifying an access token never touches the database.
- **B. Denylist:** every JWT carries a unique `jti`. Revoked `jti`s go in a table that's checked on every request. The cut-off is immediate and per token (one device), at the cost of a new table and a database check per request. Entries can be purged once the token would have expired anyway.
- **C. Per-user "tokens valid after" timestamp:** a column on the users table. Tokens whose `iat` is older are rejected. The cut-off is immediate for all of a user's tokens at once ("log out everywhere"), with one column and no new table, at the cost of a database check per request.

**Decision: A.** At this scale (5 users, all known personally) a window of at most one hour is acceptable, and there is already an emergency cut-off: deleting a user's Spotify tokens makes every tool call fail immediately, even though their JWT still verifies. A is also the easiest option to understand and explain, and it keeps the JWT choice coherent: tokens are verified purely by signature. With B or C, the obvious question is "why JWT if you hit the database anyway?".

**If requirements change:** if an immediate cut-off were needed (more users, more sensitive data), C is the next step, as it needs one column on the users table.
