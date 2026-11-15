"""Pricing analysis for a property agency: stats utils helpers."""

import logging
import random
import statistics
import time


def bootstrap_ci(values, stat=statistics.mean, n=5000, alpha=0.05, seed=11):
    rng = random.Random(seed)
    draws = sorted(stat([rng.choice(values) for _ in values]) for _ in range(n))
    return draws[int(n * alpha / 2)], draws[int(n * (1 - alpha / 2)) - 1]


def cohens_d(a, b):
    na, nb = len(a), len(b)
    pooled = (((na - 1) * statistics.variance(a)) + ((nb - 1) * statistics.variance(b))) / (na + nb - 2)
    return (statistics.mean(b) - statistics.mean(a)) / pooled ** 0.5


logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


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
