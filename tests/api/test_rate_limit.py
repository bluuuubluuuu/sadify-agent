import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient

from sadify_api.services.rate_limit import (
    RateLimitExceeded,
    RateLimitRule,
    SlidingWindowRateLimiter,
    client_key,
    rate_limit_dependency,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_allows_up_to_limit_then_blocks():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(
        RateLimitRule(max_requests=2, window_seconds=60), clock=clock
    )

    limiter.check("ip-a")
    limiter.check("ip-a")
    with pytest.raises(RateLimitExceeded) as exc:
        limiter.check("ip-a")
    assert exc.value.retry_after_seconds >= 1


def test_window_slides_and_frees_capacity():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(
        RateLimitRule(max_requests=1, window_seconds=60), clock=clock
    )

    limiter.check("ip-a")
    clock.now = 61.0
    limiter.check("ip-a")  # first hit aged out; must not raise


def test_keys_are_independent():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(
        RateLimitRule(max_requests=1, window_seconds=60), clock=clock
    )

    limiter.check("ip-a")
    limiter.check("ip-b")  # different client, own bucket


def test_client_key_prefers_forwarded_for():
    scope = {
        "type": "http",
        "headers": [(b"x-forwarded-for", b"203.0.113.7, 10.0.0.1")],
        "client": ("10.0.0.1", 1234),
    }
    assert client_key(Request(scope)) == "203.0.113.7"


def test_client_key_falls_back_to_peer():
    scope = {"type": "http", "headers": [], "client": ("192.0.2.5", 4321)}
    assert client_key(Request(scope)) == "192.0.2.5"


def test_dependency_returns_429_with_retry_after():
    limiter = SlidingWindowRateLimiter(RateLimitRule(max_requests=1, window_seconds=60))
    dep = rate_limit_dependency(limiter)
    app = FastAPI()

    @app.post("/guarded", dependencies=[Depends(dep)])
    def guarded(request: Request) -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(app)
    first = client.post("/guarded", headers={"x-forwarded-for": "203.0.113.9"})
    second = client.post("/guarded", headers={"x-forwarded-for": "203.0.113.9"})

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"]["code"] == "RATE_LIMITED"
    assert "Retry-After" in second.headers
