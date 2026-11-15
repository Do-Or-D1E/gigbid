"""V5: multi-vector items. Summary, README and code chunks are indexed separately and the
result is returned as whole projects."""
from rag.variants.base import PipelineConfig

CONFIG = PipelineConfig(name="v5_multivector", flavour="multivector", project_group=True)
