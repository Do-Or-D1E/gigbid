"""V8: corrective retrieval as a small LangGraph loop.

retrieve -> grade -> (requery once for weak requirements) -> grade -> finish
A requirement whose best evidence still grades below `rag.corrective.min_grade` is
refused: its weak items are dropped and the requirement is reported as unsupported, so
the writer cannot claim it. This targets jobs the persona should skip."""
from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from rag.variants.base import PipelineConfig

CONFIG = PipelineConfig(name="v8_corrective", corrective=True)


class Grade(BaseModel):
    requirement: str
    item_id: str
    relevance: float = Field(ge=0, le=1)


class Grades(BaseModel):
    grades: list[Grade]


class Rewrite(BaseModel):
    queries: list[str] = Field(description="One rewritten search query per weak requirement, same order")


class CState(TypedDict, total=False):
    per_query: dict[str, list[str]]
    grades: dict[str, float]
    requeried: bool
    refused: list[str]


async def run_corrective(pipe, index, q, per_query, best_chunk, mask) -> tuple[dict, list[str], dict]:
    from agent import llm, settings
    from agent.prompts import load_prompt

    min_grade = float(settings.get("rag.corrective.min_grade", 0.45))
    debug: dict[str, Any] = {"grade_calls": 0, "requeried": []}

    def snippet(item: str) -> str:
        ci = best_chunk.get(item)
        if ci is None:
            ci = next(i for i, c in enumerate(index.chunks) if c.item_id == item)
        return index.chunks[ci].text[:350]

    async def grade(state: CState) -> CState:
        rows = []
        for label, ranking in state["per_query"].items():
            req = label if label != "job" else q.title
            for item in ranking[:3]:
                rows.append(f"- requirement: {req} | item: {item} | text: {snippet(item)}")
        out, _ = await llm.call("verifier", load_prompt("evidence_grader"), "\n".join(rows)[:9000], Grades)
        debug["grade_calls"] += 1
        best: dict[str, float] = {}
        for g in out.grades:
            label = g.requirement if g.requirement in state["per_query"] else "job"
            best[label] = max(best.get(label, 0.0), g.relevance)
        return {"grades": best}

    async def requery(state: CState) -> CState:
        weak = [lbl for lbl in state["per_query"] if state["grades"].get(lbl, 0.0) < min_grade]
        out, _ = await llm.call("verifier", load_prompt("query_rewriter"),
                                "Job title: " + q.title + "\nWeak requirements:\n" + "\n".join(weak), Rewrite)
        new = dict(state["per_query"])
        for lbl, text in zip(weak, out.queries):
            ranking, _, bc = pipe._rank_items(index, text, None, mask)
            for item, ci in bc.items():
                best_chunk.setdefault(item, ci)
            new[lbl] = ranking
        debug["requeried"] = weak
        return {"per_query": new, "requeried": True}

    def route(state: CState) -> str:
        weak = [lbl for lbl in state["per_query"] if state["grades"].get(lbl, 0.0) < min_grade]
        return "requery" if weak and not state.get("requeried") else "finish"

    def finish(state: CState) -> CState:
        refused = [lbl for lbl in state["per_query"] if state["grades"].get(lbl, 0.0) < min_grade]
        pq = {lbl: ([] if lbl in refused else rk) for lbl, rk in state["per_query"].items()}
        if all(not v for v in pq.values()):
            pq = state["per_query"]  # keep ranking for metrics, but every requirement is refused
        return {"per_query": pq, "refused": [r for r in refused if r != "job"]}

    g = StateGraph(CState)
    g.add_node("grade", grade)
    g.add_node("requery", requery)
    g.add_node("regrade", grade)
    g.add_node("finish", finish)
    g.add_edge(START, "grade")
    g.add_conditional_edges("grade", route, {"requery": "requery", "finish": "finish"})
    g.add_edge("requery", "regrade")
    g.add_edge("regrade", "finish")
    g.add_edge("finish", END)
    out = await g.compile().ainvoke({"per_query": per_query})
    debug["grades"] = out.get("grades", {})
    return out["per_query"], out.get("refused", []), debug
