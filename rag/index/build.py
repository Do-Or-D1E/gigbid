"""Builds chunk lists for each index flavour.

plain        fixed chunks (V0 to V4, V7, V8)
multivector  summary + README + code views per item (V5)
contextual   fixed chunks with an LLM-generated context line prepended (V6). Only
             documents that split into 2+ chunks get a context line; single-chunk items
             already carry their whole context. One LLM call per document."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from rag.ingest.chunker import Chunk, fixed_chunks, multivector_chunks
from rag.ingest.loaders import Document, load_persona

CONTEXT_CACHE = Path(__file__).resolve().parents[2] / "data" / "processed" / "context_lines"


def _size() -> tuple[int, int]:
    from agent import settings

    return int(settings.get("rag.chunk_tokens", 180)), int(settings.get("rag.chunk_overlap", 30))


def is_persona(owner: str) -> bool:
    from rag.ingest.loaders import PERSONA_DIR

    return (PERSONA_DIR / owner / "profile.json").exists()


def user_upload_docs(user_id: str) -> list[Document]:
    """A user's own uploads, read from Postgres (tenant-scoped)."""
    from agent import settings
    from rag.ingest.loaders import load_upload

    if not settings.database_url():
        return []
    from agent import db

    with db.connect() as conn:
        rows = conn.execute("select item_id, kind, title, text from uploads where user_id=%s", (user_id,)).fetchall()
    return [load_upload(user_id, r["item_id"], r["title"], r["text"], kind=r["kind"]) for r in rows]


def build_chunks(owner: str, flavour: str = "plain", docs: list[Document] | None = None) -> list[Chunk]:
    if docs is None:
        docs = load_persona(owner) if is_persona(owner) else user_upload_docs(owner)
    size, overlap = _size()
    if flavour == "multivector":
        return [c for d in docs for c in multivector_chunks(d, size, overlap)]
    chunks = [c for d in docs for c in fixed_chunks(d, size, overlap)]
    if flavour == "contextual":
        lines = asyncio.run(context_lines(owner, docs)) if docs else {}
        for c in chunks:
            c.context = lines.get(c.chunk_id, "")
            c.view = "context" if c.context else c.view
    return chunks


async def context_lines(owner: str, docs: list[Document]) -> dict[str, str]:
    """Generate (and cache on disk) one short context line per chunk of multi-chunk documents."""
    from pydantic import BaseModel, Field

    from agent import llm
    from agent.prompts import load_prompt

    class Lines(BaseModel):
        lines: list[str] = Field(description="One context sentence per chunk, same order")

    CONTEXT_CACHE.mkdir(parents=True, exist_ok=True)
    cache_file = CONTEXT_CACHE / f"{owner}.json"
    cache: dict[str, str] = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}
    size, overlap = _size()
    system = load_prompt("contextualizer")
    sem = asyncio.Semaphore(2)

    async def one(doc: Document) -> None:
        chunks = fixed_chunks(doc, size, overlap)
        if len(chunks) < 2 or all(c.chunk_id in cache for c in chunks):
            return
        body = doc.text[:6000]
        listing = "\n\n".join(f"[chunk {i}]\n{c.text[:700]}" for i, c in enumerate(chunks))
        user = f"<document title=\"{doc.title}\" type=\"{doc.type}\">\n{body}\n</document>\n\n{listing}"
        async with sem:
            try:
                out, _ = await llm.call("contextualizer", system, user, Lines)
            except Exception:  # noqa: BLE001 - a missing context line just means no prefix
                return
        for c, line in zip(chunks, out.lines):
            cache[c.chunk_id] = line.strip()[:300]

    await asyncio.gather(*(one(d) for d in docs))
    cache_file.write_text(json.dumps(cache, indent=0, sort_keys=True), encoding="utf-8")
    return cache
