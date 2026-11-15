"""Per-token sliding-window rate limiter backed by the database (works across processes)."""

from __future__ import annotations

import hashlib
import math
import time

WINDOW_SECONDS = 60.0


def check(conn, token: str, limit: int, now: float | None = None) -> int | None:
    """Record a request for `token`. Returns None when allowed, else Retry-After seconds.

    limit <= 0 disables limiting. Rejected requests are not counted.
    """
    if limit <= 0:
        return None
    now = time.time() if now is None else now
    th = hashlib.sha256(token.encode()).hexdigest()[:24]
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("rl:" + th,))
        conn.execute("DELETE FROM rate_events WHERE token_hash = %s AND ts <= %s", (th, now - WINDOW_SECONDS))
        row = conn.execute(
            "SELECT count(*) AS c, min(ts) AS m FROM rate_events WHERE token_hash = %s", (th,)
        ).fetchone()
        if row["c"] >= limit:
            return max(1, math.ceil(row["m"] + WINDOW_SECONDS - now))
        conn.execute("INSERT INTO rate_events (token_hash, ts) VALUES (%s, %s)", (th, now))
    return None
