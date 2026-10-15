import pytest
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from spotify_mcp import rate_limit
from spotify_mcp.config import settings
from spotify_mcp.main import create_app
from spotify_mcp.oauth.tokens import issue_access_token
from spotify_mcp.rate_limit import Limit, RateLimitMiddleware, TokenBuckets


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


# --- The token bucket itself ------------------------------------------------


def test_bucket_allows_a_burst_up_to_capacity_then_refuses() -> None:
    buckets = TokenBuckets(Limit(capacity=3, refill_per_second=1), FakeClock())

    assert [buckets.try_acquire("a") for _ in range(3)] == [None, None, None]
    assert buckets.try_acquire("a") == pytest.approx(1.0)


def test_bucket_refills_at_the_configured_rate() -> None:
    clock = FakeClock()
    buckets = TokenBuckets(Limit(capacity=2, refill_per_second=0.5), clock)
    buckets.try_acquire("a")
    buckets.try_acquire("a")

    clock.now = 1.0  # half a token back
    assert buckets.try_acquire("a") == pytest.approx(1.0)
    clock.now = 2.0  # a whole token back
    assert buckets.try_acquire("a") is None


def test_bucket_never_holds_more_than_capacity() -> None:
    clock = FakeClock()
    buckets = TokenBuckets(Limit(capacity=2, refill_per_second=1), clock)
    buckets.try_acquire("a")

    clock.now = 1000.0  # a long idle period refills to capacity, not beyond
    assert [buckets.try_acquire("a") for _ in range(3)][-1] is not None


def test_each_key_has_its_own_bucket() -> None:
    buckets = TokenBuckets(Limit(capacity=1, refill_per_second=1), FakeClock())

    assert buckets.try_acquire("alice") is None
    assert buckets.try_acquire("alice") is not None
    assert buckets.try_acquire("bob") is None


def test_full_buckets_are_pruned_when_there_are_too_many(monkeypatch) -> None:
    monkeypatch.setattr(rate_limit, "_PRUNE_ABOVE", 2)
    clock = FakeClock()
    buckets = TokenBuckets(Limit(capacity=1, refill_per_second=1), clock)
    buckets.try_acquire("old-1")
    buckets.try_acquire("old-2")

    clock.now = 10.0  # both have refilled completely
    buckets.try_acquire("new")

    assert set(buckets._buckets) == {"new"}


# --- The middleware -----------------------------------------------------------


def _ok(request) -> PlainTextResponse:
    return PlainTextResponse("ok")


@pytest.fixture
def client() -> TestClient:
    """The middleware in front of a dummy app with the paths it cares about."""
    paths = ["/mcp", "/register", "/token", "/authorize", "/auth/callback", "/health"]
    app = Starlette(routes=[Route(p, _ok, methods=["GET", "POST"]) for p in paths])
    return TestClient(RateLimitMiddleware(app, clock=FakeClock()))


def _bearer(user: str) -> dict[str, str]:
    token, _ = issue_access_token(user, "client-1", [])
    return {"Authorization": f"Bearer {token}"}


def _statuses(client: TestClient, path: str, count: int, **kwargs) -> list[int]:
    return [client.post(path, **kwargs).status_code for _ in range(count)]


def test_register_is_limited_per_ip(client) -> None:
    allowed = rate_limit.REGISTER_PER_IP.capacity

    statuses = _statuses(client, "/register", allowed + 1)

    assert statuses == [200] * allowed + [429]


def test_429_says_how_long_to_wait(client) -> None:
    _statuses(client, "/register", rate_limit.REGISTER_PER_IP.capacity)

    response = client.post("/register")

    assert response.status_code == 429
    assert response.json()["error"] == "rate_limited"
    # One token of an hourly bucket of 10 takes 6 minutes to come back.
    assert response.headers["retry-after"] == "360"


def test_oauth_endpoints_share_a_per_ip_bucket(client) -> None:
    allowed = rate_limit.OAUTH_PER_IP.capacity
    _statuses(client, "/token", allowed)

    assert client.get("/authorize").status_code == 429


def test_mcp_is_limited_per_user_not_per_ip(client) -> None:
    allowed = rate_limit.MCP_PER_USER.capacity

    alice = _statuses(client, "/mcp", allowed + 1, headers=_bearer("alice"))

    assert alice[-1] == 429
    # Same IP, different user: unaffected.
    assert client.post("/mcp", headers=_bearer("bob")).status_code == 200


def test_mcp_without_a_valid_token_falls_back_to_the_ip(client) -> None:
    allowed = rate_limit.MCP_UNAUTHENTICATED_PER_IP.capacity

    statuses = _statuses(client, "/mcp", allowed + 1, headers={"Authorization": "Bearer forged"})

    assert statuses[-1] == 429
    # A real user from the same IP still gets through.
    assert client.post("/mcp", headers=_bearer("alice")).status_code == 200


def test_spoofed_forwarded_for_does_not_get_a_fresh_bucket(client) -> None:
    allowed = rate_limit.REGISTER_PER_IP.capacity
    _statuses(client, "/register", allowed)

    response = client.post("/register", headers={"X-Forwarded-For": "203.0.113.7"})

    assert response.status_code == 429


def test_trusted_client_ip_header_identifies_the_caller(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "client_ip_header", "True-Client-IP")
    allowed = rate_limit.REGISTER_PER_IP.capacity
    _statuses(client, "/register", allowed, headers={"True-Client-IP": "198.51.100.1"})

    blocked = client.post("/register", headers={"True-Client-IP": "198.51.100.1"})
    other = client.post("/register", headers={"True-Client-IP": "198.51.100.2"})

    assert blocked.status_code == 429
    assert other.status_code == 200


def test_other_paths_are_not_limited(client) -> None:
    assert set(_statuses(client, "/health", 100)) == {200}


def test_the_real_app_is_rate_limited(db_engine) -> None:
    allowed = rate_limit.REGISTER_PER_IP.capacity
    with TestClient(create_app(), base_url=settings.oauth_issuer_url) as client:
        statuses = [client.post("/register", json={}).status_code for _ in range(allowed + 1)]

    assert statuses[-1] == 429
    assert 429 not in statuses[:-1]
