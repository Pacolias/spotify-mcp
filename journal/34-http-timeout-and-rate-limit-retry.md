# HTTP timeout and 429 rate-limit retry on all Spotify API calls

**Date:** 2026-09-22

Second item of a follow-up "make it presentable" pass. Two related robustness gaps, both about what happens when Spotify itself misbehaves rather than when our code does:

**No timeout was ever set** on any `httpx.AsyncClient()` used to talk to Spotify (`spotify/client.py`'s four request helpers, and the two token calls in `spotify/auth.py`). httpx has no default timeout of its own for a client constructed without one in some configurations, and even where a default applies it's generous — a slow or hanging Spotify response would hang the calling MCP tool indefinitely instead of failing with a clear error the model/user can react to. Fixed with an explicit `httpx.Timeout(10.0, connect=5.0)` on every client.

**No handling for Spotify's 429 (rate limit) responses** — a caller would just get a raw HTTP error via `raise_for_status()`. Easy to hit in practice: `import_youtube_playlist` (entry 24) can fire a dozen-plus `search_tracks` calls back to back for one video.

**Refactor along the way**: `client.py`'s `_get`/`_post`/`_put`/`_delete` each independently built a client and sent a request — necessary duplication became a blocker for adding retry logic in one place, so they were consolidated into a single `_request(method, path, ...)` helper that the four keep their names/signatures delegating to. Fixed the timeout gap and added the 429 retry (read `Retry-After`, sleep, retry the same request once) in that one place rather than four times.

**New test**: `tests/test_rate_limit_retry.py` — mocks a 429-then-200 sequence with `respx`'s `side_effect`, monkeypatches `asyncio.sleep` so the test doesn't actually wait, and asserts both the retry happened and the delay matched the mocked `Retry-After` header.

Scope kept deliberately narrow: one retry, not a backoff/retry-forever loop — a second 429 in a row still surfaces as an error rather than silently looping, since that's more likely a real problem (wrong scope, account-level restriction) than transient rate limiting.
