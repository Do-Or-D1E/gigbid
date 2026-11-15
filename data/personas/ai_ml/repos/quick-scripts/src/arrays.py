from pathlib import Path
import json
import time

import numpy as np


def normalise(batch: np.ndarray) -> np.ndarray:
    mean = batch.mean(axis=(0, 1, 2), keepdims=True)
    std = batch.std(axis=(0, 1, 2), keepdims=True) + 1e-6
    return (batch - mean) / std


def iou(a: np.ndarray, b: np.ndarray) -> float:
    x1, y1 = np.maximum(a[:2], b[:2])
    x2, y2 = np.minimum(a[2:], b[2:])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = np.prod(a[2:] - a[:2]) + np.prod(b[2:] - b[:2]) - inter
    return float(inter / union) if union else 0.0


def retry(fn, attempts=3, delay=1.0):
    for n in range(attempts):
        try:
            return fn()
        except Exception:
            if n == attempts - 1:
                raise
            time.sleep(delay * (2 ** n))


def load_config(path: str = "config.json") -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))
