"""
Per-client sliding-window rate limiting for the HTTP API.

In-memory and per-process: fine for a single uvicorn worker. With multiple
workers/instances each keeps its own counters - use Redis (or a gateway
limiter) if you need a shared limit.
"""

import math
import time
from collections import deque
from typing import Deque, Dict

from fastapi import HTTPException, Request

from app.config.settings import settings


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._hits: Dict[str, Deque[float]] = {}
        self._last_sweep = 0.0

    def check(self, key: str, limit: int, window: float) -> float:
        """Record a hit. Returns 0.0 if allowed, else seconds until retry."""
        now = time.monotonic()
        self._sweep(now, window)

        hits = self._hits.setdefault(key, deque())
        cutoff = now - window
        while hits and hits[0] <= cutoff:
            hits.popleft()

        if len(hits) >= limit:
            return max(hits[0] + window - now, 0.001)

        hits.append(now)
        return 0.0

    def _sweep(self, now: float, window: float) -> None:
        """Drop idle clients periodically so memory stays bounded."""
        if now - self._last_sweep < window:
            return
        self._last_sweep = now
        stale = [k for k, h in self._hits.items() if not h or h[-1] <= now - window]
        for k in stale:
            del self._hits[k]

    def reset(self) -> None:
        self._hits.clear()
        self._last_sweep = 0.0


limiter = SlidingWindowRateLimiter()


def _client_key(request: Request) -> str:
    if settings.rate_limit_trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def enforce_rate_limit(request: Request) -> None:
    """FastAPI dependency: raise 429 when the client exceeds the limit."""
    if not settings.rate_limit_enabled:
        return

    retry_after = limiter.check(
        _client_key(request),
        settings.rate_limit_requests,
        settings.rate_limit_window_seconds,
    )
    if retry_after:
        seconds = math.ceil(retry_after)
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests. Please try again in {seconds} seconds.",
            headers={"Retry-After": str(seconds)},
        )
