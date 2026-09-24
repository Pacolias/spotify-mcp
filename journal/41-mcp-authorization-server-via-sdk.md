# MCP authorization: our server is the authorization server, built on the SDK's provider interface

**Date:** 2026-09-24

## Context

The remote MCP server ([entry 40](40-remote-mcp-no-monetization.md)) needs the MCP spec's OAuth 2.1 authorization. That means two chained OAuth flows:

```
  MCP host (e.g. Claude) ──(OAuth #1)──▶ our MCP server ──(OAuth #2)──▶ Spotify
  client                                 authorization server in #1       authorization server in #2
                                         client in #2
```

In #1 our server has to be an OAuth authorization server: it handles client registration, `/authorize` and `/token`, and it issues its own tokens. It must **never hand Spotify's token to the MCP client** (the spec calls this "token passthrough" and forbids it). Spotify tokens stay server-side. The MCP client only gets a token issued by us, which works only against our server and which we can revoke.

## Options considered

- **A. The official SDK's `OAuthAuthorizationServerProvider` interface** (`mcp.server.auth`, SDK v2.2.0). The SDK provides the HTTP endpoints (`/authorize`, `/token`, `/register`, `/revoke`), the RFC 8414 / RFC 9728 metadata documents, PKCE verification and bearer-token middleware. We implement a provider class that stores clients, authorization codes and tokens, and whose `authorize()` chains into Spotify's login.
- **B. An external identity provider** (Auth0, WorkOS, Keycloak...). Less security code of our own, but users would log in to the provider and then connect Spotify separately, and there are more moving parts. We'd also learn less about how OAuth works inside.
- **C. Everything from scratch.** The most learning, but hand-written security code is where vulnerabilities come from.

## Decision

**Option A.** It teaches the part that matters for MCP work (how an MCP authorization server works) without hand-rolling the security-critical mechanics. It also gives the simplest user experience: logging in to our service *is* connecting Spotify, with no separate account.

## Consequences / still to decide

- The app becomes **multi-user**. Today `SpotifyToken` is a single row fixed at `id=1` (`src/spotify_mcp/spotify/auth.py`). Spotify tokens will need to be keyed per user, and every tool call will need to resolve "which user is this bearer token for?"
- Still open, to be discussed and logged separately: the data model, the token format (opaque random tokens stored hashed vs. JWTs), hosting, the database, rate limits, and what happens to the stdio entrypoint and the `login` CLI command.
