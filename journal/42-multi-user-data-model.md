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
