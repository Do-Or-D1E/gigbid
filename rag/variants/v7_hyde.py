"""V7: HyDE. Retrieve with a hypothetical ideal proposal written for the job."""
from rag.variants.base import PipelineConfig

CONFIG = PipelineConfig(name="v7_hyde", hyde=True)
