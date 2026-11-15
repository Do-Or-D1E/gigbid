"""One configurable retrieval pipeline. Each variant module is a preset of these flags,
so every variant is "V0 plus one component" and the shipped pipeline is a combination
whose components can be ablated one at a time."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np

from agent.handoffs import EvidenceItem
from rag.index.store import ChunkIndex, get_index


@dataclass(frozen=True)
class PipelineConfig:
    name: str
    flavour: str = "plain"          # plain | contextual (V6) | multivector (V5)
    decompose: bool = False         # V1: one retrieval per extracted requirement
    hybrid: bool = False            # V2: BM25 + dense with reciprocal rank fusion
    rerank: bool = False            # V3: cross-encoder over the candidate pool
    outcome: bool = False           # V4: boost evidence linked to won / replied proposals
    project_group: bool = False     # V5: return whole projects instead of single items
    hyde: bool = False              # V7: query with a hypothetical ideal proposal
    corrective: bool = False        # V8: grade, re-query when weak, refuse when none
    candidates: int = 40
    rrf_k: int = 60

    def with_(self, **kw: Any) -> "PipelineConfig":
        return replace(self, **kw)


@dataclass
class RetrievalQuery:
    owner: str
    title: str
    description: str
    requirements: list[str] = field(default_factory=list)
    category: str = ""
    types: list[str] | None = None          # restrict to item types
    exclude_items: set[str] | None = None   # e.g. evidence the user deleted

    def job_text(self) -> str:
        return f"{self.title}\n{self.description}"


@dataclass
class RetrievalResult:
    items: list[EvidenceItem]
    per_requirement: dict[str, list[EvidenceItem]] = field(default_factory=dict)
    refused: list[str] = field(default_factory=list)
    debug: dict[str, Any] = field(default_factory=dict)

    @property
    def ranked_ids(self) -> list[str]:
        return [i.item_id for i in self.items]


# ----------------------------------------------------------------------------- helpers
def _minmax(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    lo, hi = min(scores.values()), max(scores.values())
    if hi - lo < 1e-9:
        return {k: 1.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def _rrf(rankings: list[list[str]], k: int) -> dict[str, float]:
    fused: dict[str, float] = {}
    for ranking in rankings:
        for rank, key in enumerate(ranking):
            fused[key] = fused.get(key, 0.0) + 1.0 / (k + rank + 1)
    return fused


class Pipeline:
    def __init__(self, cfg: PipelineConfig) -> None:
        self.cfg = cfg

    # -------------------------------------------------------------- chunk level
    def _chunk_scores(self, index: ChunkIndex, query: str, qvec: np.ndarray | None,
                      mask: np.ndarray | None) -> dict[int, float]:
        n = self.cfg.candidates
        dense = index.dense(qvec if qvec is not None else query, n, mask)
        if not self.cfg.hybrid:
            scores = {i: s for i, s in dense}
        else:
            sparse = index.sparse(query, n, mask)
            fused = _rrf([[str(i) for i, _ in dense], [str(i) for i, _ in sparse]], self.cfg.rrf_k)
            scores = {int(i): s for i, s in fused.items()}
        if self.cfg.rerank and scores:
            from rag.index.rerank import rerank

            top = sorted(scores, key=scores.get, reverse=True)[: self.cfg.candidates]
            rs = rerank(query, [index.chunks[i].index_text() for i in top])
            scores = {i: float(s) for i, s in zip(top, rs)}
        return scores

    def _items_from_chunks(self, index: ChunkIndex, scores: dict[int, float]) -> tuple[dict[str, float], dict[str, int]]:
        item_score: dict[str, float] = {}
        best_chunk: dict[str, int] = {}
        for ci, s in scores.items():
            item = index.chunks[ci].item_id
            if item not in item_score or s > item_score[item]:
                item_score[item] = s
                best_chunk[item] = ci
        return item_score, best_chunk

    def _outcome_boost(self, index: ChunkIndex, item_score: dict[str, float]) -> dict[str, float]:
        from agent import settings

        boost = settings.get("rag.outcome_boost", {"won": 0.25, "replied": 0.12, "ignored": -0.05})
        meta = {c.item_id: c.meta for c in index.chunks}
        won_projects = {m.get("project_id") for m in meta.values()
                        if m.get("type") == "proposal" and m.get("outcome") in ("won", "replied") and m.get("project_id")}
        norm = _minmax(item_score)
        out = {}
        for item, s in norm.items():
            m = meta.get(item, {})
            b = boost.get(m.get("outcome"), 0.0) if m.get("type") == "proposal" else 0.0
            if m.get("type") != "proposal" and m.get("project_id") in won_projects:
                b += boost.get("replied", 0.12) / 2
            out[item] = s + b
        return out

    def _group_projects(self, index: ChunkIndex, ranking: list[str]) -> list[str]:
        """V5: rank projects by their best item, then emit every item of each project."""
        proj_of: dict[str, str] = {}
        items_of: dict[str, list[str]] = {}
        for c in index.chunks:
            key = c.meta.get("project_id") or c.item_id
            proj_of[c.item_id] = key
            members = items_of.setdefault(key, [])
            # proposals are not expanded: many proposals cite the same project
            if c.item_id not in members and c.meta.get("type") != "proposal":
                members.append(c.item_id)
        out: list[str] = []
        seen: set[str] = set()
        for item in ranking:
            key = proj_of.get(item, item)
            if key in seen:
                continue
            seen.add(key)
            for i in [item] + [m for m in items_of.get(key, []) if m != item]:
                if i not in out:
                    out.append(i)
        return out

    def _rank_items(self, index: ChunkIndex, query: str, qvec: np.ndarray | None,
                    mask: np.ndarray | None) -> tuple[list[str], dict[str, float], dict[str, int]]:
        item_score, best_chunk = self._items_from_chunks(index, self._chunk_scores(index, query, qvec, mask))
        if self.cfg.outcome:
            item_score = self._outcome_boost(index, item_score)
        ranking = sorted(item_score, key=lambda i: (-item_score[i], i))
        return ranking, item_score, best_chunk

    # -------------------------------------------------------------- public
    async def retrieve(self, q: RetrievalQuery, k: int = 8) -> RetrievalResult:
        index = get_index(q.owner, self.cfg.flavour)
        mask = index.mask(q.types, q.exclude_items)
        debug: dict[str, Any] = {"variant": self.cfg.name, "queries": []}
        hyde_text = None
        if self.cfg.hyde:
            hyde_text = await _hyde(q)
            debug["hyde"] = hyde_text[:400]

        queries: list[tuple[str, str]] = []  # (label, text)
        if self.cfg.decompose and q.requirements:
            queries = [(r, f"{r}. {q.title}") for r in q.requirements]
        else:
            queries = [("job", q.job_text())]
        if hyde_text:
            queries = [(lbl, hyde_text if lbl == "job" else f"{txt}\n{hyde_text[:300]}") for lbl, txt in queries]

        per_query: dict[str, list[str]] = {}
        best_chunk: dict[str, int] = {}
        for label, text in queries:
            ranking, _, bc = self._rank_items(index, text, None, mask)
            per_query[label] = ranking
            for item, ci in bc.items():
                best_chunk.setdefault(item, ci)
            debug["queries"].append(label)

        refused: list[str] = []
        if self.cfg.corrective:
            per_query, refused, cdebug = await _corrective(self, index, q, per_query, best_chunk, mask)
            debug["corrective"] = cdebug

        if len(per_query) == 1:
            final = next(iter(per_query.values()))
        else:
            fused = _rrf(list(per_query.values()), self.cfg.rrf_k)
            final = sorted(fused, key=lambda i: (-fused[i], i))
        if self.cfg.project_group:
            final = self._group_projects(index, final)

        def item(i: str, score: float = 0.0) -> EvidenceItem:
            ci = best_chunk.get(i)
            chunk = index.chunks[ci] if ci is not None else next(c for c in index.chunks if c.item_id == i)
            m = chunk.meta
            return EvidenceItem(item_id=i, type=m.get("type", ""), title=m.get("title", ""), snippet=chunk.text[:700],
                                project_id=m.get("project_id"), date=m.get("date"), outcome=m.get("outcome"),
                                source=m.get("source", ""), score=round(score, 4))

        items = [item(i, 1.0 / (r + 1)) for r, i in enumerate(final[:k])]
        per_req = {lbl: [item(i) for i in ranking[:3]] for lbl, ranking in per_query.items() if lbl != "job"}
        return RetrievalResult(items=items, per_requirement=per_req, refused=refused, debug=debug)

    def retrieve_sync(self, q: RetrievalQuery, k: int = 8) -> RetrievalResult:
        return asyncio.run(self.retrieve(q, k))


# ----------------------------------------------------------------------------- LLM-backed steps
async def _hyde(q: RetrievalQuery) -> str:
    from agent import llm
    from agent.prompts import load_prompt

    text, _ = await llm.call("hyde", load_prompt("hyde"),
                             f"<job_post>\n{q.job_text()[:3000]}\n</job_post>")
    return str(text).strip()


async def _corrective(pipe: Pipeline, index: ChunkIndex, q: RetrievalQuery, per_query: dict[str, list[str]],
                      best_chunk: dict[str, int], mask) -> tuple[dict[str, list[str]], list[str], dict]:
    from rag.variants.v8_corrective import run_corrective

    return await run_corrective(pipe, index, q, per_query, best_chunk, mask)
