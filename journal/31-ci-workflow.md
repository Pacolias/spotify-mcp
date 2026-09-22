# CI: GitHub Actions running the test suite on every push/PR

**Date:** 2026-09-22

Second item of the "what could we improve" pass. Tests existed ([entry 11](11-test-suite.md)) but only ran when someone remembered to run them locally — nothing enforced it, and for a portfolio repo, a visitor checking whether the tests actually pass has no way to know without cloning and running them themselves.

**GitHub Actions**, not a third-party CI service: the repo is already hosted on GitHub, so it's zero extra accounts/config, and it's what anyone evaluating the repo would expect to find under the "Actions" tab.

**Real gotcha found by testing the workflow locally before trusting it**: `spotify_mcp.config` calls `sys.exit(1)` at *import* time if `SPOTIFY_CLIENT_ID` isn't set (see [entry 20](20-friendly-startup-errors.md)). Locally this is invisible because a real `.env` sits in the working directory (gitignored, never committed) — but a clean CI checkout has no `.env`, so `uv run pytest` would fail before collecting a single test. Confirmed by actually removing `.env` and running the suite in a stripped-down environment: it died with the "Missing required configuration" message.

Fixed by setting a placeholder `SPOTIFY_CLIENT_ID: ci-placeholder` in the workflow's `env:`. Safe to hardcode — it's not a secret, and the test suite never calls the real Spotify API (isolated throwaway SQLite + mocked HTTP responses, per entry 11), so the value is never actually used for anything beyond satisfying the required-config check at import.

Verified end-to-end the same way: ran `uv sync --locked --all-groups` then `uv run pytest` in a scrubbed environment (no `.env`, only `SPOTIFY_CLIENT_ID=ci-placeholder`) before pushing the workflow — all 68 tests passed, matching what the Actions run should do.

Added a status badge to the top of the project README, linking to the workflow's Actions page.
