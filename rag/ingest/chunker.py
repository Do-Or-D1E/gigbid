"""Chunkers. `fixed_chunks` is the V0 baseline (fixed windows of whitespace tokens with
overlap). `multivector_chunks` (V5) indexes a project summary, README chunks and code
chunks separately so a repo whose README says little can still be found by its code."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from rag.ingest.loaders import Document


@dataclass
class Chunk:
    chunk_id: str
    item_id: str
    text: str
    meta: dict
    view: str = "text"            # text | summary | readme | code | context
    context: str = ""             # V6 generated context line (prepended at index time)
    extra: dict = field(default_factory=dict)

    def index_text(self) -> str:
        return f"{self.context}\n{self.text}" if self.context else self.text


def _windows(words: list[str], size: int, overlap: int) -> list[list[str]]:
    if len(words) <= size:
        return [words]
    step = max(1, size - overlap)
    out = []
    for start in range(0, len(words), step):
        out.append(words[start:start + size])
        if start + size >= len(words):
            break
    return out


def fixed_chunks(doc: Document, size: int = 180, overlap: int = 30) -> list[Chunk]:
    header = f"{doc.title}. " if doc.type in ("case_study", "repo", "proposal") else ""
    words = (header + doc.text).split()
    return [Chunk(f"{doc.item_id}#c{i}", doc.item_id, " ".join(w), doc.meta())
            for i, w in enumerate(_windows(words, size, overlap))]


def _code_chunks(path: str, code: str, size: int = 60) -> list[str]:
    lines = code.splitlines()
    out = []
    for i in range(0, max(1, len(lines)), size):
        block = "\n".join(lines[i:i + size]).strip()
        if block:
            out.append(f"file {path}\n{block}")
    return out


def _summary(doc: Document) -> str:
    first = re.split(r"\n\s*\n", doc.text.strip(), maxsplit=1)[0]
    skills = ", ".join(doc.skills) if doc.skills else "unspecified"
    return f"{doc.title}. {first[:600]} Skills mentioned: {skills}."


def multivector_chunks(doc: Document, size: int = 180, overlap: int = 30) -> list[Chunk]:
    meta = doc.meta()
    chunks = [Chunk(f"{doc.item_id}#sum", doc.item_id, _summary(doc), meta, view="summary")]
    if doc.type == "repo" and doc.parts:
        readme = doc.parts.get("README.md", "")
        for i, w in enumerate(_windows(readme.split(), size, overlap)):
            if w:
                chunks.append(Chunk(f"{doc.item_id}#readme{i}", doc.item_id, " ".join(w), meta, view="readme"))
        n = 0
        for path, code in doc.parts.items():
            if path == "README.md":
                continue
            for block in _code_chunks(path, code):
                chunks.append(Chunk(f"{doc.item_id}#code{n}", doc.item_id, block, meta, view="code"))
                n += 1
    else:
        for c in fixed_chunks(doc, size, overlap):
            chunks.append(c)
    return chunks
