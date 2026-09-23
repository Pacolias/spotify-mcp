# Direction change: remote MCP server, no monetization

**Date:** 2026-09-23

## Context

The project currently runs locally over stdio ([entry 17](17-switch-to-stdio-transport.md)). The idea on the table was to turn it into a SaaS: a user visits a website, connects their Spotify account, pays (Stripe) or gets a rate-limited free tier, and receives a key to use the MCP server.

Before designing anything, we checked Spotify's current developer terms. Two findings block that idea regardless of how it's built.

## Spotify constraints

1. **User cap.** Every Web API app starts in Development Mode. Since February 2026 that means **at most 5 users** (allow-listed by hand in the developer dashboard), and the app owner must have **Spotify Premium**. Opening an app to the public requires **Extended Quota**, which since 2025 is only granted to a **legally registered business with 250,000 monthly active users** and a launched service.
2. **Developer Policy.** Streaming/playback apps **cannot be monetized** (no selling the app or access to it, no in-app purchases). This project controls playback (play, pause, queue...). The policy also says: *"Do not use the Spotify Platform or any Spotify Content to train a machine learning or AI model or otherwise ingest Spotify Content into a machine learning or AI model."* An MCP server exists to hand Spotify data to an LLM. That's a gray area for personal use, but it's not something to build a public paid service on.

A free tier with rate limits doesn't help either: the 5-user cap is hit long before rate limits would matter.

Sources:
- [Spotify Developer Policy](https://developer.spotify.com/policy)
- [February 2026 Web API Dev Mode migration guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide)
- [Web API quota updates for Development Mode (Jul 2026)](https://developer.spotify.com/blog/2026-07-23-web-api-quota-updates)
- [TechCrunch, Feb 2026](https://techcrunch.com/2026/02/06/spotify-changes-developer-mode-api-to-require-premium-accounts-limits-test-users/)

## Options considered

- **Stay local (stdio)** and spend the time on other learning goals. Works, but evaluating the project means cloning it, creating your own Spotify app and having Premium, so in practice reviewers only read the code.
- **Build the SaaS/billing side on a different API** that allows monetization. Stripe integration is general web-dev skill, less relevant to AI/MCP work.
- **Remote MCP server, no money.** Chosen.

## Decision

Turn the project into a **remote MCP server**: streamable HTTP transport plus the **MCP spec's OAuth authorization**. Users click "connect" in their MCP host (e.g. Claude) and sign in, instead of being handed an API key. Scope: the owner plus up to 4 other people (the Development Mode cap). No payments.

Reasoning: this is how companies build real MCP connectors (OAuth where the server is both a Spotify OAuth client and an authorization server for the MCP host, deployment, per-user tokens, rate limiting, observability), so it has the most learning and portfolio value. Because the 5-user cap still stops reviewers from logging in, the README will get a **short demo video**. **Evals** (measuring how well the model picks and uses the tools) come next.

This reverses [entry 17](17-switch-to-stdio-transport.md). The old Render plan and bearer-token auth from [entry 12](12-deployment-plan-and-mcp-bearer-auth.md) stay dropped; the remote version will be designed fresh around the MCP authorization spec.

## Not decided yet

How to implement it: OAuth design, hosting, database (SQLite vs Postgres), rate limits, and what happens to the stdio entrypoint. Each will be discussed and logged in its own entry before any code is written.
