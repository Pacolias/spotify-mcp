# Friendly startup errors instead of raw pydantic stacktraces

**Date:** 2026-09-22

Third and last of the "premium onboarding" improvements (see entries [18](18-cli-login-command.md) and [19](19-claude-code-registration.md)). Reproduced the bad case first: running `spotify-mcp` without `SPOTIFY_CLIENT_ID` set threw a raw `pydantic_core.ValidationError` stacktrace — not the first impression a portfolio project wants to make.

Root cause: `settings = Settings()` in `config.py` runs at **import time**, so the failure happens the instant anything imports the module — before any of our own code gets a chance to handle it gracefully.

Fix: wrapped the instantiation in `_load_settings()`, catching `pydantic.ValidationError` right there. For a missing-field error (the common case — forgot to set `SPOTIFY_CLIENT_ID`), prints which field(s) are missing plus the exact fix (`cp .env.example .env`, pointer to the README). For any other validation error (wrong type, etc.), falls back to printing pydantic's own message rather than trying to hand-craft a message for every possible case. Either way, exits with code 1 instead of a 15-line traceback.

Tested via `subprocess` rather than importing the module in-process — `sys.exit()` at import time would otherwise kill the test runner itself. Runs `python -c "import spotify_mcp.config"` in a clean tmp directory (no `.env` to accidentally pick up) with `SPOTIFY_*` env vars stripped, and asserts on the exit code and stderr message.
