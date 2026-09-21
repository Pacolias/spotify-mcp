# `spotify-mcp login`: one-command Spotify login

**Date:** 2026-09-22

First of three "premium onboarding" improvements (the other two: a `claude mcp add`-friendly registration step, and friendlier startup errors — not yet done).

Before this, logging in meant three manual steps: run `uv run uvicorn spotify_mcp.main:app`, open `http://127.0.0.1:8000/auth/login` by hand, remember to Ctrl+C afterward. Replaced with a single command, `spotify-mcp login`, via a new `typer`-based CLI (`src/spotify_mcp/cli.py`):

- No subcommand (`spotify-mcp`) still runs the MCP server over stdio — this is what an MCP host launches, unchanged.
- `spotify-mcp login` starts the login FastAPI app on a background `uvicorn.Server` (parsed host/port from `SPOTIFY_REDIRECT_URI`), opens the login URL with `webbrowser.open()`, waits on a new `asyncio.Event` (`login_complete`, set at the end of `/auth/callback`) with a timeout (default 180s), then shuts the server down and exits — either on success or on timeout (exit code 1, clear message).

`typer` was added as an explicit direct dependency — it was already present transitively via `mcp[cli]`, but importing it directly from our own code without declaring it would be fragile (a future `mcp` release could drop the extra and silently break this).

Also changed `/auth/callback`'s response from a bare JSON blob to a small HTML success page ("✅ Logged in to Spotify — you can close this tab"), independent of the CLI but part of the same "make this feel polished" pass.

**A real bug found while testing, not a code bug but a testing-methodology one**: an earlier verification run used `spotify-mcp login --timeout 3` to sanity-check the plumbing without waiting on the user. That opened a real browser tab. When the user was then asked to separately run `spotify-mcp login` themselves, they ended up clicking "Agree" on the *first* test's already-expired tab — got "Unable to connect", because that first server had already shut itself down after 3 seconds, well before a human could read Spotify's consent screen and click through. Not a bug in the login mechanism (confirmed working immediately after, with a 180s window, verified independently by checking the process's stdout and a freshly-updated token row in the database — not just taking the user's word for it). Lesson: a short-timeout automated test that opens a real browser leaves visible state (an open tab) that can bleed into a subsequent manual test if they're not clearly sequenced.

Verified end-to-end: default (no subcommand) still connects over stdio and lists all 16 tools via a real stdio client; `login` with a 3s timeout times out cleanly without hanging; `login` with a 180s timeout, run for real by the user, completed successfully — confirmed via the process's own exit code and stdout, and independently via a fresh `expires_at` timestamp in `spotify_mcp.db`.
