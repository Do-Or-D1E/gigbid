from pathlib import Path
import json
import logging
import subprocess
import sys


def smoke_test(url: str) -> None:
    out = subprocess.run(["curl", "-sf", f"{url}/healthz"], capture_output=True, text=True)
    if out.returncode != 0:
        print("health check failed", out.stderr)
        sys.exit(1)
    print("healthy:", out.stdout.strip())


def canary_ok(old_p95_ms: float, new_p95_ms: float, tolerance: float = 1.15) -> bool:
    return new_p95_ms <= old_p95_ms * tolerance


def load_config(path: str = "config.json") -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]
