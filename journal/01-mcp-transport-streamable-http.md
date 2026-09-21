# MCP transport: streamable HTTP

**Date:** 2026-09-21

Chose **streamable HTTP** over stdio for the MCP transport. stdio (the simpler default for local-only tools, where the host process spawns the server as a subprocess over stdin/stdout) would require whoever evaluates this project to run it locally with an MCP-compatible client. HTTP lets the server be deployed and evaluated without any local setup.

Trade-off accepted: HTTP transport means the server is network-reachable, so it needs its own auth layer (separate from Spotify's OAuth) to control who can talk to it — to be addressed when we get to that part.
