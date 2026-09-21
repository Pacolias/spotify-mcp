# Token storage: database (SQLite to start)

**Date:** 2026-09-21

Spotify access/refresh tokens are stored in a database rather than a flat file. SQLite to start (simple, zero external dependency), with an easy path to Postgres later if needed. Chosen over a JSON file mainly for persistence across restarts/redeploys on typical hosting setups, and because it better reflects real-world practice.
