"""Rate limiting with in-memory token buckets (journal 49).

Each caller has a bucket holding up to `capacity` tokens, refilled at a
steady rate. Every request spends one token; an empty bucket means 429. This
allows short bursts while capping the average rate.

Two kinds of caller:
- `/mcp`: the user, from the access token's `sub` (protects the Spotify
  quota, which is shared by every user of the app).
- The public OAuth endpoints, and `/mcp` without a valid token: the client
  IP, since there's no user yet.

Counters live in this process's memory, so they reset on restart and aren't
shared between server copies. That fits a single instance.
"""

import math
import time
from collections.abc import Callable
from dataclasses import dataclass

from starlette.types import ASGIApp, Receive, Scope, Send

from spotify_mcp.oauth.tokens import verify_access_token


@dataclass(frozen=True)
class Limit:
    capacity: int
    refill_per_second: float

    @classmethod
    def per_minute(cls, count: int) -> Limit:
        return cls(capacity=count, refill_per_second=count / 60)

    @classmethod
    def per_hour(cls, count: int) -> Limit:
        return cls(capacity=count, refill_per_second=count / 3600)


# Tunable. An agent legitimately chains several tool calls in a row, while a
# host registers once per "connect".
MCP_PER_USER = Limit.per_minute(60)
MCP_UNAUTHENTICATED_PER_IP = Limit.per_minute(30)
OAUTH_PER_IP = Limit.per_minute(30)
REGISTER_PER_IP = Limit.per_hour(10)

OAUTH_PATHS = frozenset({"/authorize", "/token", "/revoke", "/auth/callback"})

# Past this many buckets, drop the ones that have refilled completely: they
# carry no state worth keeping, and a flood of IPs can't grow memory forever.
_PRUNE_ABOVE = 10_000


@dataclass
class _Bucket:
    tokens: float
    updated_at: float


class TokenBuckets:
    """One bucket per key, all with the same limit."""

    def __init__(self, limit: Limit, clock: Callable[[], float] = time.monotonic) -> None:
        self._limit = limit
        self._clock = clock
        self._buckets: dict[str, _Bucket] = {}

    def try_acquire(self, key: str) -> float | None:
        """Spend a token for `key`. Returns None if allowed, otherwise how
        many seconds until a token is available."""
        now = self._clock()
        bucket = self._buckets.get(key)
        if bucket is None:
            if len(self._buckets) >= _PRUNE_ABOVE:
                self._prune(now)
            bucket = self._buckets[key] = _Bucket(self._limit.capacity, now)
        else:
            elapsed = now - bucket.updated_at
            bucket.tokens = min(
                self._limit.capacity, bucket.tokens + elapsed * self._limit.refill_per_second
            )
            bucket.updated_at = now

        if bucket.tokens >= 1:
            bucket.tokens -= 1
            return None
        return (1 - bucket.tokens) / self._limit.refill_per_second

    def _prune(self, now: float) -> None:
        full_after = self._limit.capacity / self._limit.refill_per_second
        self._buckets = {
            key: bucket
            for key, bucket in self._buckets.items()
            if now - bucket.updated_at < full_after
        }


class RateLimitMiddleware:
    """ASGI middleware applying the limits above before a request reaches
    FastAPI's routes or the mounted MCP app."""

    def __init__(self, app: ASGIApp, clock: Callable[[], float] = time.monotonic) -> None:
        self.app = app
        self._mcp_users = TokenBuckets(MCP_PER_USER, clock)
        self._mcp_anonymous = TokenBuckets(MCP_UNAUTHENTICATED_PER_IP, clock)
        self._oauth = TokenBuckets(OAUTH_PER_IP, clock)
        self._register = TokenBuckets(REGISTER_PER_IP, clock)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            retry_after = self._check(scope)
            if retry_after is not None:
                await _too_many_requests(send, retry_after)
                return
        await self.app(scope, receive, send)

    def _check(self, scope: Scope) -> float | None:
        path: str = scope["path"]
        if path == "/mcp" or path.startswith("/mcp/"):
            user = _user_from_bearer(scope)
            if user is not None:
                return self._mcp_users.try_acquire(user)
            return self._mcp_anonymous.try_acquire(_client_ip(scope))
        if path == "/register":
            return self._register.try_acquire(_client_ip(scope))
        if path in OAUTH_PATHS:
            return self._oauth.try_acquire(_client_ip(scope))
        return None


def _user_from_bearer(scope: Scope) -> str | None:
    # Signature check only, no database: the same cheap verification the SDK
    # does right after this, so a forged token can't pick someone's bucket.
    for name, value in scope["headers"]:
        if name == b"authorization":
            scheme, _, token = value.decode("latin-1").partition(" ")
            if scheme.lower() == "bearer" and token:
                access = verify_access_token(token)
                return access.subject if access else None
    return None


def _client_ip(scope: Scope) -> str:
    # Behind Render's proxy, uvicorn's proxy-headers support has already put
    # the real client address here from X-Forwarded-For (journal 49).
    client = scope.get("client")
    return client[0] if client else "unknown"


async def _too_many_requests(send: Send, retry_after: float) -> None:
    body = b'{"error":"rate_limited","error_description":"Too many requests, slow down."}'
    await send(
        {
            "type": "http.response.start",
            "status": 429,
            "headers": [
                (b"content-type", b"application/json"),
                (b"retry-after", str(math.ceil(retry_after)).encode()),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
