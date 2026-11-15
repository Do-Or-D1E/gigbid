"""Open cross-encoder reranker (fastembed ONNX). Imported lazily so the deployed app only
pays for it when the shipped pipeline uses reranking."""
from __future__ import annotations

from functools import lru_cache

import numpy as np


@lru_cache(maxsize=2)
def _model(name: str):
    from fastembed.rerank.cross_encoder import TextCrossEncoder

    from rag.index.embeddings import MODEL_DIR

    return TextCrossEncoder(model_name=name, cache_dir=str(MODEL_DIR))


def rerank(query: str, texts: list[str], model: str | None = None) -> np.ndarray:
    from agent import settings

    if not texts:
        return np.zeros(0)
    name = model or settings.get("reranker.model", "Xenova/ms-marco-MiniLM-L-6-v2")
    return np.array(list(_model(name).rerank(query, [t[:2000] for t in texts], batch_size=16)), dtype=np.float32)
