"""V4: outcome-aware ranking, boosting proposals that won or got replies and the
projects those proposals cited."""
from rag.variants.base import PipelineConfig

CONFIG = PipelineConfig(name="v4_outcome", outcome=True)
