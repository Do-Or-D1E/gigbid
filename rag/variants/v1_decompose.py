"""V1: one retrieval per requirement extracted by the Job Analyst, merged with RRF."""
from rag.variants.base import PipelineConfig

CONFIG = PipelineConfig(name="v1_decompose", decompose=True)
