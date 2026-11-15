from collections import defaultdict
from pathlib import Path
import json
import math


def chunk(text: str, size: int = 400, overlap: int = 60) -> list[str]:
    words = text.split()
    step = size - overlap
    return [" ".join(words[i:i + size]) for i in range(0, max(len(words) - overlap, 1), step)]


def cosine(a, b):
    num = sum(x * y for x, y in zip(a, b))
    den = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return num / den if den else 0.0


def top_k(query_vec, index, k=5):
    scored = [(cosine(query_vec, vec), doc_id, text) for doc_id, vec, text in index]
    return sorted(scored, reverse=True)[:k]


def build_prompt(question, hits):
    cited = "\n".join(f"[{i + 1}] {t}" for i, (_, _, t) in enumerate(hits))
    return f"Answer from the numbered passages only and cite them.\n{cited}\n\nQ: {question}"


def load_config(path: str = "config.json") -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))
