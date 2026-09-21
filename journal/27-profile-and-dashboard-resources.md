# `spotify://me/profile` and `spotify://me/dashboard` resources

**Date:** 2026-09-22

Two more resources, on top of the existing three ([entry 22](22-mcp-resources.md)):

- `spotify://me/profile`: basic identity (id, display name, follower count, profile URL/image) via `GET /me`. Simple, and a gap that had never been covered by anything — no existing tool or resource exposed even basic "who is this" info.
- `spotify://me/dashboard`: a single resource bundling now-playing + devices + top tracks + recently played into one snapshot. The point of a resource (attachable context, not an invoked action) is exactly this kind of thing — instead of a host making four separate tool calls to build a picture of "what's going on with this person's Spotify right now," one resource read returns the whole picture.

**Design choice**: each section of the dashboard is fetched independently and wrapped so one section failing (e.g. the devices call erroring) doesn't blank out the rest — only `now_playing` gates the whole resource on `NotAuthenticatedError` (since every section needs the same login anyway, checking once is enough), while devices/top_tracks/recently_played each fail to `null` individually via a small `_best_effort()` helper rather than aborting the entire response. Verified this actually behaves that way with a test that fails the devices call specifically and confirms the rest of the dashboard still comes back intact.

Verified both live against the real account through a real MCP client: `spotify://me/profile` returned real identity data, and `spotify://me/dashboard` returned a correct combined snapshot — including a track that was mid-session (Strobe, paused) from earlier testing, real devices, real top tracks, and real recently-played history, all through a single resource read.
