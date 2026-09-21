# Spotify's "discovery" endpoints are restricted for new apps — composed tools plan dropped

**Date:** 2026-09-21

The plan was to build two "composed" MCP tools — a "similar tracks" tool via `/recommendations`, and a mood/"vibe" search using `/audio-features` — as the most technically interesting tools in the project (combining Spotify data server-side rather than 1:1 wrapping an endpoint).

Before writing any code, both were checked directly against the live Spotify API with our real token, instead of assuming they'd work because the docs describe them:

```
GET /v1/recommendations           -> 404
GET /v1/audio-features/{id}       -> 403 {"error": {"status": 403}}
GET /v1/artists/{id}/top-tracks   -> 403 {"error": {"message": "Forbidden"}}
GET /v1/artists/{id}/related-artists -> 403 {"error": {"message": "Forbidden"}}
GET /v1/browse/new-releases       -> 403 {"error": {"message": "Forbidden"}}
```

All fail. The tell is in the error shape: a **plain `"Forbidden"` with no mention of scope** is a different failure mode than `"Insufficient client scope"` (seen separately when hitting `/me/top/tracks` without the right OAuth scope — that one is fixable by requesting the scope). A blanket `Forbidden` with no scope message means the *app itself* isn't allowed to call the endpoint at all, regardless of what the logged-in user has authorized.

This matches Spotify's own policy change from late 2024: several endpoints — recommendations, audio-features, audio-analysis, related-artists, artist top-tracks, several `/browse/*` endpoints, and a few others — were locked behind **"Extended Quota Mode"**, an access tier Spotify grants manually on request, generally to apps already in production with real users. A new app created today (as ours was, in this project) gets **Development Mode** by default, which doesn't include this surface. There is no scope, code change, or client-side workaround for this — the request never reaches the app's logic, it's rejected by Spotify's own gateway before that.

**Decision**: drop the "composed tools via Spotify's recommendation engine" idea entirely rather than working around it. The project moves on to the personal-data tools (top tracks/artists, recently played), playlists, and playback control — all of which, based on the *shape* of the errors seen so far, are gated by OAuth scope (fixable) rather than by this app-tier restriction. Each will still be verified against the real API before being treated as available, the same way this restriction itself was discovered — not assumed.
