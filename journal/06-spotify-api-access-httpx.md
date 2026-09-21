# Spotify API access: raw httpx, no wrapper library

**Date:** 2026-09-21

Calling the Spotify Web API directly with [httpx](https://www.python-httpx.org/) (async HTTP client) instead of a wrapper library like `spotipy`. More code to write ourselves, but it keeps the OAuth/PKCE flow and every API call fully transparent — useful both for learning MCP/OAuth properly and for showing that understanding in a portfolio project, rather than hiding it behind a third-party abstraction.
