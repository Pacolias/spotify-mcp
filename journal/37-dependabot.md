# Dependabot: weekly update PRs for uv and GitHub Actions

**Date:** 2026-09-22

Fifth and last item of the follow-up pass. Cheap, standard signal of an actively maintained repo — automatic PRs when a dependency (or a pinned GitHub Action) has a newer version, instead of dependencies silently going stale.

`.github/dependabot.yml`, two ecosystems: `uv` (covers `pyproject.toml` + `uv.lock` natively — confirmed this is real native support, not a workaround, added to Dependabot in March 2025, not something to fake via the `pip` ecosystem) and `github-actions` (keeps `actions/checkout`, `astral-sh/setup-uv`, etc. in `tests.yml` current). Both weekly.

Every update PR runs through the same CI (tests + lint, entries 31/35) before it could be merged, so this doesn't lower the bar — it just surfaces the update instead of it going unnoticed.
