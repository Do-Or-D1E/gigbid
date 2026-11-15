"""Regression harness for an AI drafting tool: track helpers."""

from pathlib import Path
import json
import logging

import mlflow


mlflow.set_tracking_uri("http://mlflow:5000")
mlflow.set_experiment("matters-nightly")


def log_run(params: dict, metrics: dict, model_path: str, promote: bool = False):
    with mlflow.start_run() as run:
        mlflow.log_params(params)
        for name, value in metrics.items():
            mlflow.log_metric(name, value)
        mlflow.log_artifact(model_path)
        if promote:
            mlflow.register_model(f"runs:/{run.info.run_id}/model", "matter-model")
        return run.info.run_id


def chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def load_config(path: str = "config.json") -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
