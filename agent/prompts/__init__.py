"""Prompt loader. Every prompt is a versioned Markdown file in this folder; no node keeps
an inline prompt. The front matter carries the version, which is logged with each run."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def _untrusted_rule() -> str:
    return (HERE / "_untrusted_data_rule.md").read_text(encoding="utf-8").strip()


@lru_cache(maxsize=None)
def _read(name: str) -> tuple[str, str]:
    text = (HERE / f"{name}.md").read_text(encoding="utf-8")
    version = "0"
    if text.startswith("---"):
        end = text.find("\n---", 3)
        for line in text[3:end].splitlines():
            if line.startswith("version:"):
                version = line.split(":", 1)[1].strip()
        text = text[end + 4:]
    import os

    rule = _untrusted_rule() if os.environ.get("GIGBID_DEFENCES", "on") != "off" else ""
    return text.strip().replace("{{UNTRUSTED_RULE}}", rule), version


def load_prompt(name: str, **fmt: object) -> str:
    text = _read(name)[0]
    for key, value in fmt.items():
        text = text.replace("{" + key + "}", str(value))
    return text


def prompt_version(name: str) -> str:
    return _read(name)[1]


def all_prompts() -> dict[str, str]:
    return {p.stem: prompt_version(p.stem) for p in sorted(HERE.glob("*.md")) if not p.stem.startswith("_")}
