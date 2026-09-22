# Ruff: linting and formatting, enforced in CI

**Date:** 2026-09-22

Third item of the follow-up pass. No static analysis or formatting tool existed at all — style was whatever each edit happened to produce by hand.

**Ruff**, not separate black + flake8/isort/pyupgrade tools: it does linting, import sorting, and formatting in one fast Rust binary, and is the standard default across the current Python ecosystem — no real alternative debate here.

**Config** (`pyproject.toml`): `line-length = 100`, rule set `["E", "F", "I", "UP", "B"]` (pycodestyle errors, pyflakes, isort, pyupgrade, bugbear). Landed on 100 empirically rather than picking a number first: ruff's default (88) flagged 78 lines across the codebase — the code was clearly already written to a wider convention than that — while 100 left only 10 genuine outliers to handle explicitly, and 110 would have started reflowing already-fine short lines back together for no benefit. One per-file ignore (`prompts.py` → `E501`): those lines are natural-language prompt text already wrapped per-sentence; forcing an 100-char hard wrap mid-sentence hurts readability for no real gain. One single-line `# noqa: E501` in `playlists.py` for one long-but-unsplittable f-string.

**Applied `ruff format` once across the whole codebase**: 7 files reformatted, all cosmetic (reflowing lines that now fit on one line at 100 cols, normalizing quote style) — reviewed the diff before accepting it, nothing behavioral.

**Real bug caught along the way, not by design**: `ruff check` flagged 9 `E402` (module-level import not at top of file) in `spotify/auth.py` — a `def _utcnow()` was sitting between two import blocks, splitting them. Not intentional; just drifted there over past edits. Fixed by moving all imports to the top of the file, ahead of the function.

**CI**: added a second `lint` job to the existing `tests.yml` workflow (entry 31), running `ruff check .` and `ruff format --check .` in parallel with the test job — both must pass for the badge to stay green.

Full test suite re-run after the reformat: still 72 passing, no behavioral changes.
