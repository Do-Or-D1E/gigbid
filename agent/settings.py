"""Loads agent/config.yaml plus environment overrides. Nothing else in the code base
hard-codes models, thresholds or budgets."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path(os.environ.get("GIGBID_CONFIG", ROOT / "agent" / "config.yaml"))


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if value and key not in os.environ:
            os.environ[key] = value


_load_dotenv()
# Trace to LangSmith only when a key is present; otherwise keep tracing local.
if not os.environ.get("LANGSMITH_API_KEY"):
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"


@lru_cache(maxsize=1)
def config() -> dict[str, Any]:
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    cfg["profile"] = os.environ.get("GIGBID_PROFILE", cfg.get("profile", "open"))
    if os.environ.get("MARKETPLACE_MODE"):
        cfg["marketplace"]["mode"] = os.environ["MARKETPLACE_MODE"]
    if os.environ.get("GIGSIM_BASE_URL"):
        cfg["marketplace"]["gigsim_base_url"] = os.environ["GIGSIM_BASE_URL"]
    if os.environ.get("MCP_TRANSPORT"):
        cfg["mcp"]["transport"] = os.environ["MCP_TRANSPORT"]
    for name in ("portfolio", "marketplace", "workspace"):
        env_key = f"MCP_{name.upper()}_URL"
        if os.environ.get(env_key):
            cfg["mcp"]["servers"][name] = os.environ[env_key]
    if os.environ.get("RAG_VARIANT"):
        cfg["rag"]["variant"] = os.environ["RAG_VARIANT"]
    if os.environ.get("POLICY_VERSION"):
        cfg["policy"]["version"] = int(os.environ["POLICY_VERSION"])
    return cfg


def reload() -> dict[str, Any]:
    config.cache_clear()
    return config()


def get(path: str, default: Any = None) -> Any:
    node: Any = config()
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def database_url() -> str | None:
    return os.environ.get("DATABASE_URL")
