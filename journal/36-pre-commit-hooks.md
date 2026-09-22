# pre-commit: ruff (check + format) plus basic hygiene hooks, run before each commit

**Date:** 2026-09-22

Fourth item of the follow-up pass, building directly on [entry 35](35-ruff-lint-and-format.md): CI catches lint/format problems on push, but only after they're already in a commit. `pre-commit` catches them locally, before the commit is made.

**Config** (`.pre-commit-config.yaml`): the official `ruff-pre-commit` hooks (`ruff-check --fix`, `ruff-format`) pinned to the same ruff version already used locally/in CI (`0.16.8`), plus four small hygiene hooks from `pre-commit-hooks` (trailing whitespace, end-of-file newline, YAML/TOML syntax) — cheap, uncontroversial checks that catch a different class of small mistake than ruff does.

Added `pre-commit` itself as a dev dependency (`uv add --group dev pre-commit`) rather than assuming a global install, so `uv run pre-commit install` works right after `uv sync` with nothing else needed.

Verified by actually running it (`uv run pre-commit run --all-files`) before trusting the config — all six hooks passed clean against the already-ruff-formatted codebase from entry 35. Installed the git hook locally afterward (`pre-commit install`); this only writes to the untracked `.git/hooks/`, so each clone needs to run it once — documented in a new "Linting and formatting" README section.

Not made mandatory/enforced beyond the README instruction — the actual gate is still CI (entry 31/35), which runs regardless of whether a given clone remembered to install the local hook.
