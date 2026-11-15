"""V0 baseline: fixed chunks, top-k cosine on the whole job post."""
from rag.variants.base import PipelineConfig

CONFIG = PipelineConfig(name="v0_naive")
