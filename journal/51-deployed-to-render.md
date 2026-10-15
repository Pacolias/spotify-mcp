# Deployed: Render + Neon, CD from GitHub Actions, and what testing in production found

**Date:** 2026-10-15

Implements [entries 48–50](48-deployment-render-neon-docker-cicd.md): the server is live on Render, with Postgres on Neon, and Claude Code is connected to it through the MCP OAuth flow.

## What was built

- **Rate limiting** ([entry 49](49-rate-limiting-design.md)): an ASGI middleware with in-memory token buckets. `/mcp` gets 60/min per user (the JWT's `sub`, verified by signature), OAuth endpoints 30/min per IP, and `/register` 10/hour per IP. `/mcp` without a valid token falls back to the per-IP bucket. Over-limit requests get `429` with `Retry-After`. Buckets that have refilled are pruned past 10,000 entries, so a flood of IPs can't grow memory without bound.
- **Postgres** with psycopg 3. `DATABASE_URL` accepts Neon's `postgresql://` URLs, and the engine pings pooled connections because Neon scales to zero.
- **Alembic** ([entry 50](50-alembic-migrations.md)): migrations live in `src/spotify_mcp/migrations/` and are applied at startup. Render's free plan has no pre-deploy step, and there's a single instance, so concurrent upgrades can't happen. A database created by `create_all` before Alembic is stamped at the baseline revision instead of being recreated; the local development database was adopted that way, with no data lost. A test checks that the migrations produce exactly the models' schema.
- **Docker**: a two-stage build with uv and the locked dependencies, 285 MB. It runs as a non-root user and listens on `$PORT`.
- **CI/CD**: tests run on both SQLite and a Postgres service container, the image is built on every push, and a `deploy` job runs only on `main` after all of that passes. It calls the Render deploy hook (`RENDER_DEPLOY_HOOK_URL` secret) and fails loudly if the secret is missing. Render's auto-deploy is off.

## What testing against real systems found

Each of these passed every unit test and only showed up against the real thing.

1. **Foreign keys.** Postgres enforces them and SQLite (by default) doesn't. Running the suite on Postgres showed a user and their credentials being inserted in no guaranteed order. The login now flushes the user first, and CI runs on Postgres so this can't come back.
2. **Secrets in error messages.** pydantic's validation errors echo the rejected value, so an invalid `DATABASE_URL` (with its password) or a short `JWT_SIGNING_KEY` would have been printed to the logs. Startup errors now show only the field and the reason.
3. **A line break in `DATABASE_URL`.** It was pasted into Render's dashboard across two lines and surfaced as a DNS error for a host name containing `\n`. The setting now rejects whitespace with a message that says exactly that.
4. **The client IP behind Render.** The per-IP limits need the real client address, and it was checked by sending forged headers to the live service:
   - `X-Forwarded-For`: Render appends the real IP but keeps the client's value first, so it's forgeable.
   - `True-Client-IP`: reaches the app exactly as the client sent it, so it's forgeable. A third-party claim that Cloudflare overwrites it turned out to be wrong here, and it was briefly the configured header.
   - `CF-Connecting-IP`: a request that arrives with one already set is rejected by Render's Cloudflare edge with `403`, so any value the app sees was set by Cloudflare.

   `CLIENT_IP_HEADER=cf-connecting-ip` is now configured. Re-tested live: with a different forged `X-Forwarded-For` and `True-Client-IP` on every request, the limit still triggers after ~30 requests. The per-user limit on `/mcp` was never affected, because it keys on the signed JWT.

## Incident: production secrets exposed in a screenshot

While the Render environment was being filled in, a screenshot with the values visible (Neon password, `JWT_SIGNING_KEY`, `TOKEN_ENCRYPTION_KEY`) was shared in the AI assistant conversation. All three are treated as compromised and must be rotated (a new Neon password, two new keys). Rotating is cheap while the only user is the owner: they just reconnect once. Takeaway: hide secret values (the dashboard's eye toggle) before sharing screenshots, and treat anything shared as compromised.

## Verified

Claude Code connected to `https://spotify-mcp-xgpa.onrender.com/mcp`: `/mcp` → Authenticate → Spotify consent → connected. `now_playing` and `top_artists` then returned the account's real data from production. The URL got a `-xgpa` suffix because `spotify-mcp.onrender.com` was taken, so the three URL settings and the Spotify redirect URI use it.
