"""Retention study for a meal-kit startup: cohorts helpers."""

from pathlib import Path
import json
import logging
import time

import pandas as pd


def retention_table(events: pd.DataFrame) -> pd.DataFrame:
    events = events.copy()
    events["cohort"] = events.groupby("user_id")["ts"].transform("min").dt.to_period("M")
    events["age"] = (events["ts"].dt.to_period("M") - events["cohort"]).apply(lambda p: p.n)
    counts = events.groupby(["cohort", "age"])["user_id"].nunique().unstack(fill_value=0)
    return counts.div(counts[0], axis=0).round(3)


def load_config(path: str = "config.json") -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def retry(fn, attempts=3, delay=1.0):
    for n in range(attempts):
        try:
            return fn()
        except Exception:
            if n == attempts - 1:
                raise
            time.sleep(delay * (2 ** n))
