# Spotify auth: OAuth2 Authorization Code + PKCE

**Date:** 2026-09-21

Spotify auth uses OAuth2. Chose the **Authorization Code flow with PKCE** over the classic Authorization Code + client_secret flow — it's Spotify's current recommendation, and avoids having to carefully guard a long-lived client secret in favor of a per-flow dynamically generated verifier/challenge pair.

The OAuth callback (Spotify redirects the user's browser back after consent) is a regular route inside the same FastAPI app — this is needed regardless of which MCP transport is chosen, since the consent step always goes through a browser.
