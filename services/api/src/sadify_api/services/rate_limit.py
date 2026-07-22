"""In-process sliding-window rate limiter for guest-open, model-heavy routes.

Cost-safety, not perfect security. The Q&A analysis and agent-finalize routes
are intentionally guest-open (no login required to try SADify), which also means
no per-user quota gates them. A single script can loop them and drive Vertex
token cost against the billing account. This limiter caps request rate per
client so that abuse is bounded.

Honest limitation: the window state lives in process memory, so the limit is
enforced *per Cloud Run instance*, not globally. At scale-to-zero with a small
`max-instances` ceiling this is adequate as a first line — the platform instance
cap is the real hard ceiling. A globally-consistent limit would need a shared
store (Firestore/Redis); that is deliberately not built here because there are
no users yet. See CLAUDE.md Phase 8.

Client identity is the first hop in X-Forwarded-For (the real caller on Cloud
Run, where request.client is Google's front end), falling back to the direct
peer for local/dev.
"""

from collections import deque
from dataclasses import dataclass
from threading import Lock
import time

from fastapi import HTTPException, Request


@dataclass(frozen=True)
class RateLimitRule:
    max_requests: int
    window_seconds: float


class SlidingWindowRateLimiter:
    """Thread-safe sliding-window counter keyed by an opaque client string."""

    def __init__(self, rule: RateLimitRule, *, clock=time.monotonic) -> None:
        self._rule = rule
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def check(self, key: str) -> None:
        """Record one hit for `key`; raise RateLimitExceeded if over the rule."""
        now = self._clock()
        cutoff = now - self._rule.window_seconds
        with self._lock:
            bucket = self._hits.get(key)
            if bucket is None:
                bucket = deque()
                self._hits[key] = bucket
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self._rule.max_requests:
                retry_after = max(1, int(bucket[0] + self._rule.window_seconds - now))
                raise RateLimitExceeded(retry_after_seconds=retry_after)
            bucket.append(now)


class RateLimitExceeded(Exception):
    def __init__(self, *, retry_after_seconds: int) -> None:
        super().__init__("Rate limit exceeded")
        self.retry_after_seconds = retry_after_seconds


def client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    if request.client is not None and request.client.host:
        return request.client.host
    return "unknown"


def rate_limit_dependency(limiter: SlidingWindowRateLimiter):
    """Build a FastAPI dependency that enforces `limiter` per client key."""

    def _enforce(request: Request) -> None:
        try:
            limiter.check(client_key(request))
        except RateLimitExceeded as exc:
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "RATE_LIMITED",
                    "message": (
                        "Too many requests. Please wait a moment and try again."
                    ),
                },
                headers={"Retry-After": str(exc.retry_after_seconds)},
            ) from exc

    return _enforce
