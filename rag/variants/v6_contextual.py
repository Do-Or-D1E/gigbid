"""V6: contextual retrieval. A generated context line is prepended to each chunk of
multi-chunk documents before embedding and BM25 indexing."""
from rag.variants.base import PipelineConfig

CONFIG = PipelineConfig(name="v6_contextual", flavour="contextual")
