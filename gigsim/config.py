"""Environment-driven settings for GigSim."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def resolve_path(p: str | os.PathLike[str]) -> Path:
    """Absolute paths are kept; relative ones resolve against the cwd, then the repo root."""
    path = Path(p)
    if path.is_absolute():
        return path
    if (Path.cwd() / path).exists():
        return (Path.cwd() / path).resolve()
    return (REPO_ROOT / path).resolve()


@dataclass
class Settings:
    database_url: str
    admin_token: str = "gigsim-admin-dev"
    rate_limit_per_min: int = 60
    error_rate: float = 0.02
    time_scale: float = 60.0
    policy_version: str = "1"
    client_mode: str = "heuristic"  # llm | heuristic
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    seed_dir: Path = field(default_factory=lambda: resolve_path("gigsim/seed"))
    data_dir: Path = field(default_factory=lambda: resolve_path("data"))
    error_seed: int = 4016
    stream_interval_hours: float = 0.25  # used when a stream job has release_order but no offset
    weekly_allowance: int = 80

    @classmethod
    def from_env(cls, **overrides) -> "Settings":
        env = os.environ
        url = overrides.pop("database_url", None) or env.get("GIGSIM_DATABASE_URL")
        if not url:
            raise RuntimeError("GIGSIM_DATABASE_URL is required (Postgres URI)")
        api_key = env.get("GIGSIM_LLM_API_KEY") or env.get("OPENAI_API_KEY") or None
        mode = (env.get("GIGSIM_CLIENT_MODE") or ("llm" if api_key else "heuristic")).lower()
        if mode not in ("llm", "heuristic"):
            raise RuntimeError("GIGSIM_CLIENT_MODE must be 'llm' or 'heuristic'")
        s = cls(
            database_url=url,
            admin_token=env.get("GIGSIM_ADMIN_TOKEN", "gigsim-admin-dev"),
            rate_limit_per_min=int(env.get("GIGSIM_RATE_LIMIT_PER_MIN", "60")),
            error_rate=float(env.get("GIGSIM_ERROR_RATE", "0.02")),
            time_scale=float(env.get("GIGSIM_TIME_SCALE", "60")),
            policy_version=str(env.get("GIGSIM_POLICY_VERSION", "1")),
            client_mode=mode,
            llm_model=env.get("GIGSIM_LLM_MODEL", "gpt-4o-mini"),
            llm_base_url=env.get("GIGSIM_LLM_BASE_URL") or None,
            llm_api_key=api_key,
            seed_dir=resolve_path(env.get("GIGSIM_SEED_DIR", "gigsim/seed")),
            data_dir=resolve_path(env.get("GIGSIM_DATA_DIR", "data")),
            error_seed=int(env.get("GIGSIM_ERROR_SEED", "4016")),
            stream_interval_hours=float(env.get("GIGSIM_STREAM_INTERVAL_HOURS", "0.25")),
        )
        for k, v in overrides.items():
            setattr(s, k, v)
        return s
