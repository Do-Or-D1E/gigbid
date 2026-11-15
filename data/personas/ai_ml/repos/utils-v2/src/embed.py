from pathlib import Path
import json
import logging
import time

from sentence_transformers import SentenceTransformer


_model = SentenceTransformer("all-MiniLM-L6-v2")


def embed(texts: list[str], batch_size: int = 64):
    return _model.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                         show_progress_bar=False).tolist()


logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def load_config(path: str = "config.json") -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def retry(fn, attempts=3, delay=1.0):
    for n in range(attempts):
        try:
            return fn()
        except Exception:
            if n == attempts - 1:
                raise
            time.sleep(delay * (2 ** n))
