# License (MIT), author attribution, and a text-based usage example

**Date:** 2026-09-22

Fourth and last item of the "what could we improve" pass — pure presentation, no code behavior changed. Discussed with the user first rather than picked unilaterally, since license choice and what to say about the author are personal/legal calls, not engineering ones.

**License: MIT.** Added `LICENSE` at the repo root and `license = "MIT"` to `pyproject.toml` (PEP 639 SPDX string form — confirmed `uv sync` still builds fine with it). Chosen for being the most permissive/standard option for a portfolio repo: anyone evaluating it can clone, run, and reuse it with minimal friction, with no explicit alternative (Apache 2.0, all-rights-reserved) preferred.

**Author attribution**: added a byline in the README intro ("a portfolio project by [Paco Molina](https://pacomolina.dev)") and a short `## Author` section at the bottom linking the same site — the user's own choice over a bare GitHub-profile link.

**No real demo (gif/screenshot)**: can't record one from here. Added a text-based `## Example` section instead, right after the intro — a realistic transcript of the `import_youtube_playlist` exchange from [journal entry 24](24-youtube-playlist-import.md), since that's real, already-verified behavior rather than an invented example. A visual demo is still a better artifact for a visitor skimming the repo; left as a follow-up for the user to record themselves if they want one later.
