"""
rate_limit.py — simple in-process rate limiter (no Redis required).

Uses a sliding-window counter stored in a dict. Safe for single-process
deployments (Render free tier runs one Uvicorn worker).

If you later scale to multiple workers, swap the in-memory store for
a Redis-backed one — the interface stays the same.

Usage:
    from rate_limit import rate_limit_check
    await rate_limit_check(key="login:192.168.1.1", limit=10, window_seconds=60)
"""

import time
import asyncio
from collections import defaultdict, deque
from fastapi import HTTPException, Request


# ip -> deque of timestamps (sliding window)
_windows: dict[str, deque] = defaultdict(deque)
_lock = asyncio.Lock()


async def rate_limit_check(key: str, limit: int, window_seconds: int) -> None:
    """
    Raise HTTP 429 if `key` has been called more than `limit` times
    in the last `window_seconds` seconds.
    """
    async with _lock:
        now   = time.monotonic()
        cutoff = now - window_seconds
        dq = _windows[key]

        # Evict timestamps outside the window
        while dq and dq[0] < cutoff:
            dq.popleft()

        if len(dq) >= limit:
            retry_after = int(window_seconds - (now - dq[0])) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

        dq.append(now)


def get_client_ip(request: Request) -> str:
    """
    Return the real client IP, respecting X-Forwarded-For (Render uses a proxy).
    Falls back to request.client.host.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── Pre-built limit presets ──────────────────────────────────────────────────

async def limit_login(request: Request) -> None:
    """10 login attempts per IP per minute."""
    ip = get_client_ip(request)
    await rate_limit_check(f"login:{ip}", limit=10, window_seconds=60)


async def limit_password_reset(request: Request) -> None:
    """5 password-reset requests per IP per 15 minutes."""
    ip = get_client_ip(request)
    await rate_limit_check(f"pwreset:{ip}", limit=5, window_seconds=900)


async def limit_otp(request: Request) -> None:
    """10 OTP verifications per IP per 5 minutes."""
    ip = get_client_ip(request)
    await rate_limit_check(f"otp:{ip}", limit=10, window_seconds=300)
