"""Chunk indexes. One `ChunkIndex` holds the chunks of one owner (persona or user) for one
index flavour (plain | contextual | multivector) with a dense matrix and a BM25 index.
Dense search runs in numpy for evals; the deployed app keeps the same vectors in pgvector
(see rag/index/pgvector.py) and the parity test checks both return the same ranking."""
from __future__ import annotations

import json
import re
import threading
from dataclasses import asdict
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from rag.index.embeddings import Embedder, get_embedder
from rag.ingest.chunker import Chunk

PROCESSED = Path(__file__).resolve().parents[2] / "data" / "processed"
_TOKEN = re.compile(r"[a-z0-9][a-z0-9+#.\-]*[a-z0-9+#]|[a-z0-9]")
_STOP = set("""a an the and or of to in on for with by from at as is are was were be been this that it its
into our your their we you they i me my he she them his her not no but if then so than too very can will just
about over under more most other some such only own same also any each few both all""".split())


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]


class ChunkIndex:
    def __init__(self, chunks: list[Chunk], vectors: np.ndarray, embedder: Embedder) -> None:
        self.chunks = chunks
        self.vectors = vectors.astype(np.float32)
        self.embedder = embedder
        self._bm25 = BM25Okapi([tokenize(c.index_text()) for c in chunks]) if chunks else None
        self.by_id = {c.chunk_id: i for i, c in enumerate(chunks)}

    # ------------------------------------------------------------------ search
    def dense(self, query: str | np.ndarray, k: int, mask: np.ndarray | None = None) -> list[tuple[int, float]]:
        if not self.chunks:
            return []
        q = self.embedder.embed_one(query) if isinstance(query, str) else query
        sims = self.vectors @ q
        if mask is not None:
            sims = np.where(mask, sims, -np.inf)
        k = min(k, len(sims))
        idx = np.argpartition(-sims, k - 1)[:k]
        idx = idx[np.argsort(-sims[idx], kind="stable")]
        return [(int(i), float(sims[i])) for i in idx if np.isfinite(sims[i])]

    def sparse(self, query: str, k: int, mask: np.ndarray | None = None) -> list[tuple[int, float]]:
        if not self._bm25:
            return []
        scores = np.asarray(self._bm25.get_scores(tokenize(query)), dtype=np.float64)
        if mask is not None:
            scores = np.where(mask, scores, -np.inf)
        k = min(k, len(scores))
        idx = np.argpartition(-scores, k - 1)[:k]
        idx = idx[np.argsort(-scores[idx], kind="stable")]
        return [(int(i), float(scores[i])) for i in idx if np.isfinite(scores[i]) and scores[i] > 0]

    def mask(self, types: list[str] | None = None, exclude_items: set[str] | None = None) -> np.ndarray | None:
        if not types and not exclude_items:
            return None
        return np.array([(not types or c.meta.get("type") in types)
                         and (not exclude_items or c.item_id not in exclude_items) for c in self.chunks])

    # ------------------------------------------------------------------ persistence
    def save(self, folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        with open(folder / "chunks.jsonl", "w", encoding="utf-8") as fh:
            for c in self.chunks:
                fh.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
        np.save(folder / f"emb__{self.embedder.name.replace('/', '__')}.npy", self.vectors)

    @classmethod
    def load(cls, folder: Path, embedder: Embedder) -> "ChunkIndex":
        chunks = [Chunk(**json.loads(line)) for line in (folder / "chunks.jsonl").read_text(encoding="utf-8").splitlines()]
        emb_path = folder / f"emb__{embedder.name.replace('/', '__')}.npy"
        if emb_path.exists():
            vectors = np.load(emb_path)
        else:
            vectors = embedder.embed([c.index_text() for c in chunks]) if chunks else np.zeros((0, embedder.dim))
            np.save(emb_path, vectors)
        return cls(chunks, vectors, embedder)

    @classmethod
    def build(cls, chunks: list[Chunk], embedder: Embedder) -> "ChunkIndex":
        vectors = embedder.embed([c.index_text() for c in chunks]) if chunks else np.zeros((0, embedder.dim))
        return cls(chunks, vectors, embedder)

    def add(self, new_chunks: list[Chunk]) -> None:
        """Incremental re-index when the user adds work in the UI."""
        keep = [c for c in self.chunks if c.item_id not in {n.item_id for n in new_chunks}]
        keep_vec = self.vectors[[self.by_id[c.chunk_id] for c in keep]] if keep else np.zeros((0, self.embedder.dim))
        new_vec = self.embedder.embed([c.index_text() for c in new_chunks])
        self.__init__(keep + new_chunks, np.vstack([keep_vec, new_vec]), self.embedder)


_lock = threading.Lock()
_cache: dict[tuple, ChunkIndex] = {}


def get_index(owner: str, flavour: str = "plain", embed_model: str | None = None) -> ChunkIndex:
    """Load (or build on first use) the index for an owner. Flavours: plain, contextual, multivector."""
    embedder = get_embedder(embed_model)
    key = (owner, flavour, embedder.name)
    with _lock:
        if key in _cache:
            return _cache[key]
        from rag.index.build import build_chunks, is_persona

        folder = PROCESSED / flavour / owner
        if is_persona(owner) and (folder / "chunks.jsonl").exists():
            idx = ChunkIndex.load(folder, embedder)
        else:
            idx = ChunkIndex.build(build_chunks(owner, flavour), embedder)
            if is_persona(owner):
                idx.save(folder)  # user upload indexes are small and rebuilt from Postgres
        _cache[key] = idx
        return idx


def is_cached(owner: str, flavour: str = "plain") -> bool:
    return any(k[0] == owner and k[1] == flavour for k in _cache)


def invalidate(owner: str | None = None) -> None:
    with _lock:
        for key in list(_cache):
            if owner is None or key[0] == owner:
                _cache.pop(key)
