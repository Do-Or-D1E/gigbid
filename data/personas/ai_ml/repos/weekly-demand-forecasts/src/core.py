from collections import defaultdict, deque

import pandas as pd


def load_shipments(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", dayfirst=True)
    df["amount"] = pd.to_numeric(df["amount"].str.replace(",", ""), errors="coerce")
    df = df.dropna(subset=["created_at"]).drop_duplicates(subset=["shipment_id"])
    return df


def monthly(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby(df["created_at"].dt.to_period("M"))["amount"]
              .agg(["count", "sum", "mean"]).reset_index())


def rolling_features(events, window=30):
    """events: iterable of dicts sorted by ts with keys shipment_id, ts, value."""
    buf = defaultdict(lambda: deque(maxlen=window))
    out = []
    for e in events:
        hist = buf[e["shipment_id"]]
        vals = [h["value"] for h in hist]
        out.append({
            "shipment_id": e["shipment_id"],
            "ts": e["ts"],
            "n_prev": len(vals),
            "mean_prev": sum(vals) / len(vals) if vals else 0.0,
            "max_prev": max(vals) if vals else 0.0,
            "gap_days": (e["ts"] - hist[-1]["ts"]).days if hist else -1,
        })
        hist.append(e)
    return out
