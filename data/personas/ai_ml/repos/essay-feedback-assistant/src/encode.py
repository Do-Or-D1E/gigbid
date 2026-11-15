from pathlib import Path
import json
import logging

from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch


MODEL_ID = "distilbert-base-uncased"
tok = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID, num_labels=6)


@torch.no_grad()
def predict(texts, batch_size=32):
    out = []
    for i in range(0, len(texts), batch_size):
        batch = tok(texts[i:i + batch_size], truncation=True, padding=True, max_length=256,
                    return_tensors="pt")
        logits = model(**batch).logits
        out.extend(logits.softmax(-1).argmax(-1).tolist())
    return out


def load_config(path: str = "config.json") -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
