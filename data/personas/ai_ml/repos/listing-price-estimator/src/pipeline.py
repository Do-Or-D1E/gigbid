from collections import defaultdict, deque
import subprocess
import sys

import pandas as pd


def load_listings(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", dayfirst=True)
    df["amount"] = pd.to_numeric(df["amount"].str.replace(",", ""), errors="coerce")
    df = df.dropna(subset=["created_at"]).drop_duplicates(subset=["listing_id"])
    return df


def monthly(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby(df["created_at"].dt.to_period("M"))["amount"]
              .agg(["count", "sum", "mean"]).reset_index())


def smoke_test(url: str) -> None:
    out = subprocess.run(["curl", "-sf", f"{url}/healthz"], capture_output=True, text=True)
    if out.returncode != 0:
        print("health check failed", out.stderr)
        sys.exit(1)
    print("healthy:", out.stdout.strip())


def canary_ok(old_p95_ms: float, new_p95_ms: float, tolerance: float = 1.15) -> bool:
    return new_p95_ms <= old_p95_ms * tolerance


def rolling_features(events, window=30):
    """events: iterable of dicts sorted by ts with keys listing_id, ts, value."""
    buf = defaultdict(lambda: deque(maxlen=window))
    out = []
    for e in events:
        hist = buf[e["listing_id"]]
        vals = [h["value"] for h in hist]
        out.append({
            "listing_id": e["listing_id"],
            "ts": e["ts"],
            "n_prev": len(vals),
            "mean_prev": sum(vals) / len(vals) if vals else 0.0,
            "max_prev": max(vals) if vals else 0.0,
            "gap_days": (e["ts"] - hist[-1]["ts"]).days if hist else -1,
        })
        hist.append(e)
    return out
