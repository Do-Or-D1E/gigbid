"""Open embedding models that run on a CPU. `potion` is a model2vec static model
(minishlab/potion-base-8M, MIT): numpy only, fast enough for serverless. `bge` is
BAAI/bge-small-en-v1.5 through fastembed (ONNX). Which one ships is decided in evals."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import numpy as np

MODEL_DIR = Path(os.environ.get("GIGBID_MODEL_DIR", Path(__file__).resolve().parents[2] / "cache" / "models"))


class Embedder:
    name: str
    dim: int

    def embed(self, texts: list[str]) -> np.ndarray:  # pragma: no cover - interface
        raise NotImplementedError

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed([text])[0]


def _normalise(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    n = np.linalg.norm(x, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return x / n


class PotionEmbedder(Embedder):
    def __init__(self, model: str = "minishlab/potion-base-8M") -> None:
        from model2vec import StaticModel

        local = MODEL_DIR / model.replace("/", "__")
        if local.exists():
            self._m = StaticModel.from_pretrained(str(local))
        else:
            self._m = StaticModel.from_pretrained(model)
            try:
                local.parent.mkdir(parents=True, exist_ok=True)
                self._m.save_pretrained(str(local))
            except OSError:
                pass
        self.name = model
        self.dim = int(self._m.dim)

    def embed(self, texts: list[str]) -> np.ndarray:
        return _normalise(self._m.encode(texts, show_progress_bar=False))


class FastEmbedder(Embedder):
    def __init__(self, model: str = "BAAI/bge-small-en-v1.5") -> None:
        from fastembed import TextEmbedding

        self._m = TextEmbedding(model_name=model, cache_dir=str(MODEL_DIR))
        self.name = model
        self.dim = len(next(iter(self._m.embed(["probe"]))))

    def embed(self, texts: list[str]) -> np.ndarray:
        return _normalise(np.array(list(self._m.embed(texts, batch_size=32))))


@lru_cache(maxsize=4)
def get_embedder(model: str | None = None) -> Embedder:
    from agent import settings

    model = model or settings.get("embeddings.model", "minishlab/potion-base-8M")
    if model.startswith("minishlab/"):
        return PotionEmbedder(model)
    return FastEmbedder(model)
