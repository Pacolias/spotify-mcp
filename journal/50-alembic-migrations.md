# Database migrations with Alembic

**Date:** 2026-10-15

Moving to Postgres on Neon ([entry 48](48-deployment-render-neon-docker-cicd.md)) means the production database holds real data that has to survive schema changes. Until now the schema came from SQLModel's `create_all`, and an incompatible change meant dropping a table ([entry 43](43-multi-user-storage-implemented.md)).

## Options

- **A. Alembic**, the standard migration tool for SQLAlchemy (which SQLModel is built on). Each schema change is a versioned script in the repo, applied in order on deploy. It's what production teams use. Downsides: one more tool, and one more step in the deploy.
- **B. Keep `create_all`:** it creates missing tables and nothing else. Simpler, but it never alters an existing table, so any change to a table with data means manual SQL or dropping it (and every user reconnecting).

## Decision

**A, Alembic** (decided by the user).
