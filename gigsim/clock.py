"""Simulated clock. All simulated instants are integer microseconds since the Unix epoch ("us")."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
SIM_EPOCH = datetime(2026, 11, 1, 9, 0, 0, tzinfo=timezone.utc)
US_PER_HOUR = 3_600_000_000
US_PER_WEEK = 7 * 24 * US_PER_HOUR


def to_us(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = dt - UNIX_EPOCH
    return (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds


def from_us(us: int) -> datetime:
    return UNIX_EPOCH + timedelta(microseconds=int(us))


def iso(us: int | None) -> str | None:
    if us is None:
        return None
    return from_us(us).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_iso(s: str | None) -> int | None:
    if not s:
        return None
    try:
        return to_us(datetime.fromisoformat(str(s).replace("Z", "+00:00")))
    except ValueError:
        return None


EPOCH_US = to_us(SIM_EPOCH)


def hours_to_us(h: float) -> int:
    return int(round(h * US_PER_HOUR))


def new_clock_state(scale: float, real_now: float | None = None) -> dict:
    """Clock state persisted in the DB: sim_now = base_us + (real - start_real) * scale."""
    return {
        "start_real": real_now if real_now is not None else time.time(),
        "base_us": EPOCH_US,
        "scale": float(scale),
        "advanced_hours": 0.0,
    }


def sim_now_us(state: dict, real_now: float | None = None) -> int:
    real = real_now if real_now is not None else time.time()
    elapsed = max(0.0, real - state["start_real"])
    return int(state["base_us"] + elapsed * state["scale"] * 1_000_000)


def week_start_us(now_us: int) -> int:
    idx = max(0, (now_us - EPOCH_US) // US_PER_WEEK)
    return EPOCH_US + idx * US_PER_WEEK
