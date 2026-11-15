"""Pricing analysis for a property agency: plots helpers."""

from pathlib import Path
import json
import logging

import matplotlib.pyplot as plt


def trend_chart(months, values, title, path):
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(months, values, marker="o", linewidth=2)
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.annotate(f"{values[-1]:,.0f}", (months[-1], values[-1]), textcoords="offset points", xytext=(6, 6))
    fig.tight_layout()
    fig.savefig(path, dpi=160)


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
