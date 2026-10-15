# Deployment: Render, Neon Postgres, our own Docker image, deploys from GitHub Actions

**Date:** 2026-10-15

The remote server works locally ([entry 47](47-http-transport-implemented.md)). These decisions cover where and how it runs in production. The constraint was **free hosting**. All decisions were made by the user after reviewing the options.

## 1. Hosting: Render (free plan)

GitHub Pages was ruled out first: it serves static files only, and this is a Python server that has to run continuously.

**Options (checked against their state in October 2026):**
- **Render, free plan:** deploys from the GitHub repo, with HTTPS and a public URL out of the box (Spotify requires HTTPS for non-loopback redirect URIs). No credit card. Downsides: it spins down after 15 minutes without traffic and takes about a minute to wake up, and its disk is ephemeral, so files written at runtime are lost on every restart or deploy.
- **Oracle Cloud Always Free:** a full VM with a persistent disk, and the most to learn about running Linux. Downsides: it needs a card, the free ARM allowance was halved in August 2026, popular regions often have no capacity, and HTTPS, the domain and hardening are all on us.
- **Google Cloud Run:** a generous free tier for low traffic. Downsides: it needs a card, has no persistent disk, and its managed database isn't free.
- **Fly.io / Koyeb:** no longer realistic free options (Fly.io dropped its free tier, and Koyeb now places a card hold at sign-up).

**Decision: Render.** Trade-off accepted: the first request after an idle period is slow (cold start).

## 2. Database: Postgres on Neon

Render's free disk is ephemeral, so SQLite (a file on that disk) would lose every user and token on each restart. A managed database outside Render is needed.

**Decision: Postgres, hosted on Neon's free plan** (0.5 GB per project, scales to zero when idle). It's also the database a production service would realistically use. SQLite stays only as the throwaway database in tests (to be revisited if tests need Postgres-specific behaviour).

## 3. Rate limiting: yes

The reasons it was raised:
- Spotify rate-limits **per app**, not per user, so one user's agent stuck in a loop could exhaust the quota for everyone.
- `/register` and the other OAuth endpoints are open to the whole internet.
- Free-tier CPU and database compute are small, and abuse could exhaust them.

The counter-argument: five known users, and Spotify's `429` is already handled with a backoff and retry ([entry 34](34-http-timeout-and-rate-limit-retry.md)).

**Decision: add rate limiting.** What to limit and how is decided in its own entry.

## 4. Our own Docker image

**Options:**
- **A. Our own Dockerfile**, built by Render. We control the exact runtime, the image runs the same anywhere (so it's portable to another host), and it's Docker practice. Downside: one more file to maintain, and the image should also be built in CI to catch breakage.
- **B. Render's native Python runtime.** Simpler, with no Dockerfile. Downsides: it's tied to Render's conventions, isn't portable, and gives no Docker practice.

**Decision: A.**

## 5. Continuous deployment from GitHub Actions, gated on CI

**Options:**
- **A. Render watches the repo** and deploys on every push to `main`. Simplest, but the deploy isn't explicitly tied to the test results.
- **B. GitHub Actions triggers the deploy** (through a Render deploy hook) only after every check has passed on `main`. The tests → deploy chain is explicit and lives in the repo. Downsides: more configuration, and a secret (the hook URL) stored in GitHub.

**Decision: B.** Render's own auto-deploy will be turned off, so the only way to production is through green CI.
