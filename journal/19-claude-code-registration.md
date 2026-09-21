# Registration via `claude mcp add` instead of manual JSON editing

**Date:** 2026-09-22

Second of the three "premium onboarding" improvements (see [entry 18](18-cli-login-command.md) for the first). Editing a host's MCP config JSON by hand is exactly the kind of fiddly step that erodes a "premium" first impression — Claude Code has a built-in command for this, `claude mcp add`, checked directly (`claude mcp add --help`) rather than assumed:

```bash
claude mcp add spotify-mcp -- uv run --directory "$(pwd)" spotify-mcp
```

README now leads with this one-liner for Claude Code, keeping the generic JSON snippet underneath for other hosts.

Verified for real, not just read from `--help`: ran the exact command against this repo, then `claude mcp list`, which showed `spotify-mcp: uv run --directory /home/paco/Documents/spotify-mcp spotify-mcp - ✔ Connected` — registered and actually connected through a real Claude Code instance, not just our own test MCP client.
