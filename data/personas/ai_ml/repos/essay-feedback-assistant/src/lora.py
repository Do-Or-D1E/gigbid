from pathlib import Path
import json
import logging

from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, Trainer, TrainingArguments


def make_trainer(base_id, train_ds, eval_ds, out_dir="out/lora"):
    model = AutoModelForCausalLM.from_pretrained(base_id)
    cfg = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, target_modules=["q_proj", "v_proj"],
                     task_type="CAUSAL_LM")
    model = get_peft_model(model, cfg)
    args = TrainingArguments(output_dir=out_dir, num_train_epochs=3, per_device_train_batch_size=8,
                             learning_rate=2e-4, evaluation_strategy="epoch", logging_steps=25)
    return Trainer(model=model, args=args, train_dataset=train_ds, eval_dataset=eval_ds)


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
