"""Retriever factory: the variant is chosen by config (`rag.variant`), never in code.
`best` reads its component flags from evals/results/rag_decision.json, which the RAG
evaluation writes, so the shipped design is the measured one."""
from __future__ import annotations

import importlib
import json
from pathlib import Path

from rag.variants.base import Pipeline, PipelineConfig, RetrievalQuery, RetrievalResult  # noqa: F401

VARIANTS = ["v0_naive", "v1_decompose", "v2_hybrid", "v3_rerank", "v4_outcome", "v5_multivector",
            "v6_contextual", "v7_hyde", "v8_corrective"]
DECISION = Path(__file__).resolve().parents[1] / "evals" / "results" / "rag_decision.json"


def variant_config(name: str) -> PipelineConfig:
    if name == "best":
        if DECISION.exists():
            flags = json.loads(DECISION.read_text(encoding="utf-8"))["shipped"]["flags"]
            return PipelineConfig(name="best", **flags)
        return PipelineConfig(name="best", decompose=True, hybrid=True)
    return importlib.import_module(f"rag.variants.{name}").CONFIG


def get_pipeline(name: str | None = None) -> Pipeline:
    from agent import settings

    return Pipeline(variant_config(name or settings.get("rag.variant", "best")))
