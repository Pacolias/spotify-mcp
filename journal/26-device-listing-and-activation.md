# `list_devices` / `activate_device` — and why "start Spotify from nothing" isn't possible

**Date:** 2026-09-22

Prompted by: "can the LLM make Spotify start playing from the MCP, even if nothing's open?" Answered that directly before writing any code: **no, not truly** — the Spotify Web API is a remote-control layer for Spotify Connect, and can only act on a device that's *already running somewhere* (phone, desktop app, web player). It cannot launch the Spotify application itself; every playback tool built so far already depended on this ("No active device found" is exactly this limitation surfacing).

Given that, scoped the actual work to what's real: **seeing what devices already exist** and **switching/activating one**, rather than attempting a "cold start" (e.g. auto-opening `open.spotify.com` or shelling out to launch a desktop client) — that path was discussed and explicitly deferred as a separate, platform-dependent, best-effort feature, not bundled in silently.

Added `user-read-playback-state` scope (another re-login — third scope-driven re-login in the project so far), then:
- `list_devices`: `GET /me/player/devices`, returns name/type/id/active-status/volume for every device Spotify currently knows about.
- `activate_device`: `PUT /me/player` with `{"device_ids": [id], "play": bool}`, switches playback to a specific device and optionally starts it.

**Small honest finding while testing live**: right after transferring playback to a second real device, immediately re-listing devices still showed the *old* device as active — not a bug in the transfer call (`204` succeeded), just eventual consistency on Spotify's side. A re-check ~2 seconds later showed the correct device as active. Not worth adding an artificial delay or retry loop for — noted here so it's not mistaken for a broken `activate_device` if seen again. Reverted the account back to its original active device afterward, out of courtesy, since this test used the user's actual devices rather than a disposable one.

`list_devices`'s docstring says outright that this can only see/activate already-open Spotify instances, not launch new ones — so the model doesn't present "nothing found" as a bug it can route around.
