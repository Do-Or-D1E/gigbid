"""V3: dense candidates reranked by an open cross-encoder (precision at small k)."""
from rag.variants.base import PipelineConfig

CONFIG = PipelineConfig(name="v3_rerank", rerank=True, candidates=30)
