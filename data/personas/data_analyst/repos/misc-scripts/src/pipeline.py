import logging
import re

import matplotlib.pyplot as plt
import pandas as pd


def clean_names(s: pd.Series) -> pd.Series:
    return (s.str.strip().str.lower().str.replace(r"\s+", " ", regex=True)
              .str.replace(r"[^a-z0-9 &'-]", "", regex=True))


def dedupe(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    df = df.sort_values("updated_at").drop_duplicates(subset=keys, keep="last")
    df["phone"] = df["phone"].astype(str).str.replace(r"\D", "", regex=True).str[-10:]
    return df.reset_index(drop=True)


def trend_chart(months, values, title, path):
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(months, values, marker="o", linewidth=2)
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.annotate(f"{values[-1]:,.0f}", (months[-1], values[-1]), textcoords="offset points", xytext=(6, 6))
    fig.tight_layout()
    fig.savefig(path, dpi=160)


logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
