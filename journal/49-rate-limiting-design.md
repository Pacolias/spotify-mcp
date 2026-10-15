# Rate limiting: per user and per IP, in-memory token buckets, our own middleware

**Date:** 2026-10-15

[Entry 48](48-deployment-render-neon-docker-cicd.md) decided to rate-limit. This entry covers what to limit and how. Each decision was made by the user after reviewing the options.

## 1. What: both per user and per IP

- **Per user, on `/mcp`** (tool calls), identified by the access token. It protects the shared Spotify quota from a looping agent, and one user hitting the limit doesn't affect the others. It doesn't stop anonymous traffic, which never reaches the tools anyway.
- **Per IP, on the public OAuth endpoints** (`/register`, `/authorize`, `/token`, `/revoke`), where there's no user yet. It protects against registration spam and hammering `/token`. Limitation: people behind one network share an IP, and someone with many IPs can get around it.

**Decision: both.**

## 2. Where counters live: in memory

- **In memory:** no new dependency and fast. Counters reset on restart, which on Render's free plan happens whenever the service spins down, and several server copies would each count separately.
- **Shared store (Redis):** counters survive restarts and work across copies. Downsides: one more external service, extra latency, and the server depends on it to start.

**Decision: in memory.** It fits a single instance. Moving to Redis is the next step if the service ever runs as several copies.

## 3. Implementation: our own middleware

- **slowapi**, the common FastAPI rate limiter, built around decorators on FastAPI routes. Our OAuth and `/mcp` routes come from the SDK's mounted app, so it doesn't fit without adapting it.
- **Our own small ASGI middleware**, which runs on every request before it reaches the mounted app.

**Decision: our own middleware.** Trade-off accepted: it's security-relevant code we write ourselves, so it gets thorough tests.

## 4. Algorithm: token bucket

- **Fixed window** ("at most N per minute"): simplest, but allows bursts of up to 2N around a window boundary.
- **Token bucket:** each caller has a bucket that refills at a steady rate, and each request spends a token. Short bursts are allowed and the average is capped. Widely used by large APIs.

**Decision: token bucket.** The concrete rates are implementation details, tunable later.
