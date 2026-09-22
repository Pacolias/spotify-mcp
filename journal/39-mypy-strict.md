# mypy --strict, enforced in CI and pre-commit

**Date:** 2026-09-22

Second item of the third follow-up pass, after ruff (entry 35) which lints and formats but doesn't check types. Went straight for `strict = true` rather than a looser config — the codebase was already fully type-hinted, so strict mode's job was mostly confirming that, not fighting it.

**Findings from the first run (25 errors), and how each was resolved — not blanket-ignored:**
- **`yt_dlp` had no type stubs.** `types-yt-dlp` exists on PyPI and is actively published against yt-dlp's own release cadence — added as a dev dependency rather than silencing the import.
- **`pydantic-settings`'s `Settings()` call looked like a missing required argument** (`spotify_client_id` has no default — it's meant to come from the environment at runtime, which mypy can't see statically). Fixed properly by enabling `plugins = ["pydantic.mypy"]`, which teaches mypy how pydantic's settings/model machinery actually works, rather than papering over it with a local ignore.
- **22 "Missing type arguments for generic type dict" errors**, concentrated in `spotify/client.py` and `mcp/resources.py` — every function returning raw Spotify API JSON was typed as bare `dict`/`list[dict]`. Parametrized all of them to `dict[str, Any]` (the actually-correct type for arbitrary, heterogeneous JSON objects here — a full per-field `TypedDict` for every Spotify response shape would be a much bigger, not-obviously-worthwhile undertaking for internal glue code that's immediately consumed by string formatting).
- **One real stub-strictness mismatch**, not a bug: `yt_dlp.YoutubeDL`'s stub types its constructor against a private, fully-keyed `_YoutubeDLOptions` TypedDict that a plain dict literal doesn't structurally satisfy. Not worth importing a private stub-only type to work around; left a single scoped `# type: ignore[arg-type]` with a comment explaining why, rather than loosening strictness project-wide for one call site.
- **One genuinely missing annotation**: `main.py`'s FastAPI `lifespan` function had no return type — added `-> AsyncIterator[None]`.

**Wired in everywhere else already gates on green**: added a `mypy` step to the `lint` CI job (entry 31/35), and a `local` pre-commit hook (entry 36) that runs `uv run mypy` via `language: system` rather than pre-commit's own isolated mypy environment — this reuses the project's actual installed library types (fastapi, sqlmodel, pydantic, the new yt-dlp stubs) exactly like CI does, instead of duplicating that list through `additional_dependencies` and risking the two drifting apart.

Verified with `pre-commit run --all-files` (all seven hooks pass) and a full `pytest` run (120 passed) after the type-driven edits, to confirm nothing behavioral slipped in alongside the type fixes.
