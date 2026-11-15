"""V2: BM25 plus dense retrieval fused with reciprocal rank fusion (exact tool names)."""
from rag.variants.base import PipelineConfig

CONFIG = PipelineConfig(name="v2_hybrid", hybrid=True)
