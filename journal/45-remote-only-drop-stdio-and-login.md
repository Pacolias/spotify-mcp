# Remote only: the stdio entrypoint and the `login` command go away

**Date:** 2026-10-15

## Context

Today the server runs locally: the MCP host launches it over **stdio** (entry 17), and a separate `spotify-mcp login` command runs a small local web server to complete the Spotify login in the browser (entry 18). The remote version covers both of these: streamable HTTP replaces stdio, and the OAuth provider (entry 44) makes Spotify login part of clicking "connect" in the MCP host. The open question from entries 40 and 41 was whether the local pieces stay alongside the remote ones.

## Options considered

- **A. Remote only.** Remove stdio and `login`. One code path. The single-user shortcuts go away (`user_id=None` meaning "the only stored user", in-memory pending logins), so there's less to maintain and test. Downsides: using the server, even for the owner, needs the HTTP server running (locally on `localhost` during development, or deployed). Someone cloning the repo can no longer just launch it over stdio, though in practice they already need their own Spotify app and Premium.
- **B. Both.** Keep the local mode next to the remote one. It works without hosting, someone cloning the repo can run it, and it's a fallback if the remote server is down. Downsides: two entrypoints and two auth paths in the same codebase, the single-user shortcuts stay, and Spotify needs two registered redirect URIs that the code has to tell apart.

## Decision

**A, remote only** (decided by the user).

## Consequences

- During development the same HTTP server runs on `localhost` and the MCP host connects to it there, going through the full OAuth flow. Spotify accepts plain-HTTP redirect URIs only on loopback addresses, so the deployed server will need HTTPS.
- There's a single Spotify callback route, used by the remote OAuth flow.
- Sequencing: the local pieces are removed in the same step that brings in the HTTP transport, so there's never a commit where the server can't be used at all.
