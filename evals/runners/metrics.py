"""Metric helpers shared by every eval runner."""
from __future__ import annotations

import math
from typing import Iterable


def recall_at_k(ranked: list[str], relevant: dict[str, int], k: int) -> float | None:
    if not relevant:
        return None
    return len(set(ranked[:k]) & set(relevant)) / len(relevant)


def mrr(ranked: list[str], relevant: dict[str, int]) -> float | None:
    if not relevant:
        return None
    for i, item in enumerate(ranked):
        if item in relevant:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(ranked: list[str], relevant: dict[str, int], k: int) -> float | None:
    if not relevant:
        return None
    dcg = sum((2 ** relevant.get(item, 0) - 1) / math.log2(i + 2) for i, item in enumerate(ranked[:k]))
    ideal = sorted(relevant.values(), reverse=True)[:k]
    idcg = sum((2 ** g - 1) / math.log2(i + 2) for i, g in enumerate(ideal))
    return dcg / idcg if idcg else 0.0


def mean(values: Iterable[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 4) if vals else None


def prf(pred: list[bool], gold: list[bool]) -> dict[str, float | int]:
    tp = sum(p and g for p, g in zip(pred, gold))
    fp = sum(p and not g for p, g in zip(pred, gold))
    fn = sum(g and not p for p, g in zip(pred, gold))
    tn = sum((not p) and (not g) for p, g in zip(pred, gold))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4),
            "tp": tp, "fp": fp, "fn": fn, "tn": tn, "n": len(gold)}


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    v = sorted(values)
    pos = (len(v) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return round(v[lo] + (v[hi] - v[lo]) * (pos - lo), 3)


def cohen_kappa(a: list, b: list) -> float | None:
    if not a or len(a) != len(b):
        return None
    labels = sorted(set(a) | set(b))
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(lbl) / n) * (b.count(lbl) / n) for lbl in labels)
    return round((po - pe) / (1 - pe), 4) if pe < 1 else 1.0


def bootstrap_ci(values: list[float], iters: int = 2000, seed: int = 4016) -> tuple[float, float] | None:
    import random

    if len(values) < 2:
        return None
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(values) for _ in values) / len(values) for _ in range(iters))
    return round(means[int(0.025 * iters)], 4), round(means[int(0.975 * iters)], 4)
