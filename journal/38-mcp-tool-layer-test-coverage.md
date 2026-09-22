# Closing the MCP-tool-layer coverage gap, and enforcing coverage in CI

**Date:** 2026-09-22

First and third items of a third follow-up pass. Measured coverage before touching anything (`pytest --cov`, not yet added to the project): 66% overall, but the number hid a specific, real gap — `spotify/client.py` (97%) and `spotify/auth.py` (87%) were well tested, while the thin MCP-tool wrapper layer sitting on top of them was not: `mcp/tools/playback.py` 28%, `personal.py` 30%, `playlists.py` 40%, `library.py` 47%. That's exactly the layer that formats what the model sees and maps exceptions to user-facing strings — a bug there (wrong f-string, wrong exception caught) wouldn't be caught by anything that already existed, since existing tests mostly verified "does the HTTP call do the right thing," not "does the tool present the result/error correctly."

**New test files**, one per under-covered tools module (`test_playback_tools.py`, `test_personal_tools.py`, `test_playlist_tools.py`, `test_library_tools.py`): each monkeypatches the already-well-tested client function the tool calls, rather than re-mocking HTTP with `respx` — the point was testing the tool's own logic (message formatting, empty-result messages, exception→string mapping, input validation like `seek`'s negative-position check), not re-proving the HTTP layer works.

**Result**: 66% → 87% overall (`playback.py` 82%, `personal.py` 87%, `playlists.py` 85%, `library.py` 97%). Deliberately stopped short of 100%: the remaining misses in `playback.py` are the identical `except (NotAuthenticatedError, SpotifyPlaybackError) as exc: return str(exc)` one-liner repeated across ~9 tools, already exercised by `pause()`'s and `list_devices()`'s error-path tests — testing the same one-line pattern nine more times with different function names is padding, not coverage.

**Coverage now measured and gated in CI**, not just an ad hoc local number:
- `[tool.coverage.run]` omits `cli.py` — the login/serve entrypoint, which is exercised via subprocess (`test_config_errors.py`) and by hand against real Spotify (entry 11), not by unit tests, so counting its 0% against the total would misrepresent what's actually covered vs. genuinely untestable this way.
- `[tool.coverage.report] fail_under = 78` — below the current 87% (headroom for normal fluctuation) but well above the old 66%, so a real regression back toward "the tool layer stopped being tested" would fail CI.
- `tests.yml`'s `pytest` job now runs `pytest --cov --cov-report=term-missing`, so the per-file table is visible in every CI run's log, not just discoverable by someone running `--cov` locally.

**No coverage badge added.** A live percentage badge (like the Tests/License ones already in the README) needs either an external service (Codecov/Coveralls — a real account-creation decision) or a self-hosted badge step that commits an SVG back to the repo. Neither felt worth it for what the CI log already surfaces; flagged here rather than done silently, in case it's wanted later.
