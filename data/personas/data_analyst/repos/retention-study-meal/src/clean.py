"""Retention study for a meal-kit startup: clean helpers."""

import time

import pandas as pd


def load_orders(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", dayfirst=True)
    df["amount"] = pd.to_numeric(df["amount"].str.replace(",", ""), errors="coerce")
    df = df.dropna(subset=["created_at"]).drop_duplicates(subset=["order_id"])
    return df


def monthly(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby(df["created_at"].dt.to_period("M"))["amount"]
              .agg(["count", "sum", "mean"]).reset_index())


def chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def retry(fn, attempts=3, delay=1.0):
    for n in range(attempts):
        try:
            return fn()
        except Exception:
            if n == attempts - 1:
                raise
            time.sleep(delay * (2 ** n))
