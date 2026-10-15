# Streamable HTTP transport: app structure, user resolution, stateless sessions

**Date:** 2026-10-15

Design decisions for the HTTP transport step of the remote server ([entry 40](40-remote-mcp-no-monetization.md), [entry 45](45-remote-only-drop-stdio-and-login.md)). Each one was made by the user after reviewing the options.

## 1. FastAPI is the main app; the SDK's app is mounted inside it

The remote server serves three things: the MCP endpoint (`/mcp`), the SDK's OAuth routes (`/authorize`, `/token`, metadata...) and the Spotify callback route.

**Options:**
- **A. FastAPI as the main app, with the SDK's Starlette app mounted inside.** Keeps FastAPI as the project's base (as the declared stack says), with its validation and docs for our own routes (health, callback, error pages). Downside: FastAPI doesn't forward startup/shutdown (`lifespan`) events to mounted apps, so the SDK's session manager has to be started by hand (the gotcha from [entry 08](08-mcp-sdk-api-drift-and-mounting-gotcha.md)), and there are two app layers.
- **B. Only the SDK's app**, adding our routes with `custom_route`. One layer, no lifespan workaround, less code. Downside: FastAPI leaves the project and the declared stack changes; our own routes are plain Starlette.

**Decision: A.**

## 2. The user is passed explicitly to every Spotify call

Each tool has to call Spotify with the right user's tokens. The SDK verifies the JWT on every request and puts it in a *contextvar* (a Python variable with a separate value per in-flight request). Today every Spotify call goes through one function, `_request` in `spotify/client.py`.

**Options:**
- **A. Implicit:** `_request` reads the user from the SDK's contextvar. Only that one function changes. Downside: the dependency is invisible in function signatures, and code running outside a request (a test, a background task) has no user and fails at runtime, not when it's written.
- **B. Explicit:** each tool resolves the user once and passes `user_id` down through every client function to `_request`. Visible in every signature, checked by mypy, and tests don't depend on ambient context. Downside: every client function and tool signature changes, with a lot of repetitive plumbing.

**Decision: B.**

## 3. Stateless HTTP sessions

In streamable HTTP the server can keep a **session** per connected client, remembered across requests.

**Options:**
- **A. Stateful** (the SDK default): sessions live in server memory, and the server can push messages to the client on its own initiative (notifications, progress). Downside: with several server copies behind a load balancer, each client has to stick to the same copy, and a restart drops open sessions.
- **B. Stateless** (`stateless_http`): every request stands alone, so any copy of the server can handle it. It scales horizontally and restarts are harmless. Downside: the server can't initiate messages to the client. None of the current tools need that, but it closes that door.

**Decision: B.**
