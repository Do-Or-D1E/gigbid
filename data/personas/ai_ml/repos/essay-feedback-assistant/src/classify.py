"""Essay feedback assistant: classify helpers."""

from collections import Counter, defaultdict
from pathlib import Path
import json
import math
import re


TOKEN = re.compile(r"[a-z0-9']+")


class NaiveBayes:
    def __init__(self):
        self.words = defaultdict(Counter)
        self.docs = Counter()

    def fit(self, texts, labels):
        for t, y in zip(texts, labels):
            self.docs[y] += 1
            self.words[y].update(TOKEN.findall(t.lower()))

    def predict(self, text):
        toks = TOKEN.findall(text.lower())
        best, best_lp = None, -1e18
        for y, n in self.docs.items():
            total = sum(self.words[y].values()) + len(self.words[y]) + 1
            lp = math.log(n / sum(self.docs.values()))
            lp += sum(math.log((self.words[y][w] + 1) / total) for w in toks)
            if lp > best_lp:
                best, best_lp = y, lp
        return best


def load_config(path: str = "config.json") -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))
