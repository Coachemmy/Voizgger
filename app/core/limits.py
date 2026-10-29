"""Demo guards so a public deployment cannot drain the Meta API credits.

Two independent limits:
  * a per-IP sliding window on every AI endpoint (stops floods and scanners)
  * a daily ceiling on calls that actually spend credits (stops slow drains)

Both are disabled with DEMO_LIMITS_ENABLED=0, which is what local runs want.
"""
import os
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.db import _connect

DAILY_LIMIT = int(os.getenv("DEMO_DAILY_LIMIT", "50"))
IP_LIMIT = int(os.getenv("DEMO_IP_LIMIT", "5"))
IP_WINDOW_SECONDS = int(os.getenv("DEMO_IP_WINDOW", "60"))
LIMITS_ENABLED = os.getenv("DEMO_LIMITS_ENABLED", "1") != "0"

QUOTA_MESSAGE = "Daily demo quota reached. Watch the demo video to see the full flow."
RATE_MESSAGE = "Too many requests. Please wait a minute and try again."

_ip_hits: dict[str, deque] = defaultdict(deque)


class LimitExceeded(Exception):
    """Raised when a guard blocks a request. Rendered as 429 by main.py."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _today() -> str:
    return time.strftime("%Y-%m-%d")


def rate_limit(request: Request) -> None:
    """Dependency: cap how often one client may hit the AI endpoints."""
    if not LIMITS_ENABLED:
        return

    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    hits = _ip_hits[ip]
    while hits and now - hits[0] > IP_WINDOW_SECONDS:
        hits.popleft()
    if len(hits) >= IP_LIMIT:
        raise LimitExceeded(RATE_MESSAGE)
    hits.append(now)


def reserve_ai_call() -> None:
    """Claim one slot of the daily budget right before spending credits."""
    if not LIMITS_ENABLED:
        return

    day = _today()
    with _connect() as conn:
        row = conn.execute("SELECT count FROM usage WHERE day = ?", (day,)).fetchone()
        used = (row["count"] if row else 0) + 1
        conn.execute(
            "INSERT INTO usage (day, count) VALUES (?, ?) "
            "ON CONFLICT(day) DO UPDATE SET count = excluded.count",
            (day, used),
        )

    if used > DAILY_LIMIT:
        raise LimitExceeded(QUOTA_MESSAGE)


def reset_limits() -> None:
    """Test helper: forget in-memory windows and wipe today's usage."""
    _ip_hits.clear()
    with _connect() as conn:
        conn.execute("DELETE FROM usage")
