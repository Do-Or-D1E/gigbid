"""Loaders for every portfolio source: PDF CV, Markdown case studies, repo READMEs and code,
client reviews, past proposals, and user uploads. Each returns `Document`s with the
metadata the retrievers and filters need (persona, type, project, skills, date, client
industry and, for proposals, outcome)."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import yaml

from rag.ingest.skills import tag_skills

ROOT = Path(__file__).resolve().parents[2]
PERSONA_DIR = ROOT / "data" / "personas"
CODE_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".sql", ".yaml", ".yml", ".toml", ".ipynb", ".r", ".sh", ".json"}


@dataclass
class Document:
    item_id: str
    type: str                       # cv | case_study | repo | review | proposal | upload
    title: str
    text: str
    owner: str                      # persona id or user id
    project_id: str | None = None
    date: str | None = None
    client_industry: str | None = None
    outcome: str | None = None      # proposals only: won | replied | ignored
    source: str = ""
    skills: list[str] = field(default_factory=list)
    parts: dict[str, str] = field(default_factory=dict)  # repos: readme / code files, for multi-vector

    def meta(self) -> dict:
        return {
            "item_id": self.item_id, "type": self.type, "title": self.title, "owner": self.owner,
            "project_id": self.project_id, "date": self.date, "client_industry": self.client_industry,
            "outcome": self.outcome, "source": self.source, "skills": self.skills,
        }


def _front_matter(text: str) -> tuple[dict, str]:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            meta = yaml.safe_load(text[3:end]) or {}
            return meta, text[end + 4:].lstrip("\n")
    return {}, text


def load_cv(pdir: Path, owner: str) -> list[Document]:
    pdf = pdir / "cv.pdf"
    if pdf.exists():
        from pypdf import PdfReader

        text = "\n".join((p.extract_text() or "") for p in PdfReader(str(pdf)).pages)
        source = str(pdf.relative_to(ROOT))
    elif (pdir / "cv.md").exists():
        text = (pdir / "cv.md").read_text(encoding="utf-8")
        source = str((pdir / "cv.md").relative_to(ROOT))
    else:
        return []
    text = re.sub(r"[ \t]+", " ", text).strip()
    return [Document(f"{owner}-cv", "cv", "Curriculum vitae", text, owner, source=source, skills=tag_skills(text))]


def load_case_studies(pdir: Path, owner: str) -> list[Document]:
    out = []
    for path in sorted((pdir / "case_studies").glob("*.md")):
        meta, body = _front_matter(path.read_text(encoding="utf-8"))
        out.append(Document(
            item_id=str(meta.get("item_id", path.stem)), type="case_study", title=str(meta.get("title", path.stem)),
            text=body.strip(), owner=owner, project_id=meta.get("project_id"), date=str(meta.get("date", "")) or None,
            client_industry=meta.get("client_industry"), source=str(path.relative_to(ROOT)),
            skills=tag_skills(body),
        ))
    return out


def load_repos(pdir: Path, owner: str) -> list[Document]:
    out = []
    for repo in sorted(p for p in (pdir / "repos").glob("*") if p.is_dir()):
        meta = json.loads((repo / "meta.json").read_text(encoding="utf-8")) if (repo / "meta.json").exists() else {}
        readme = (repo / "README.md").read_text(encoding="utf-8") if (repo / "README.md").exists() else ""
        parts = {"README.md": readme}
        for f in sorted(repo.rglob("*")):
            if f.is_file() and f.suffix.lower() in CODE_EXT and f.name != "meta.json":
                parts[str(f.relative_to(repo)).replace("\\", "/")] = f.read_text(encoding="utf-8", errors="ignore")
        full = "\n\n".join(f"# file: {k}\n{v}" for k, v in parts.items())
        out.append(Document(
            item_id=str(meta.get("item_id", f"{owner}-repo-{repo.name}")), type="repo",
            title=f"Repository {meta.get('slug', repo.name)}", text=full, owner=owner,
            project_id=meta.get("project_id"), date=meta.get("date"), source=str(repo.relative_to(ROOT)),
            skills=tag_skills(full), parts=parts,
        ))
    return out


def _jsonl(path: Path) -> Iterable[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line.strip()]


def load_reviews(pdir: Path, owner: str) -> list[Document]:
    return [Document(
        item_id=r["item_id"], type="review", title=f"Client review ({r.get('rating')}/5)", text=r["text"], owner=owner,
        project_id=r.get("project_id"), date=r.get("date"), client_industry=r.get("client_industry"),
        source=f"data/personas/{owner}/reviews.jsonl", skills=tag_skills(r["text"]),
    ) for r in _jsonl(pdir / "reviews.jsonl")]


def load_proposals(pdir: Path, owner: str) -> list[Document]:
    out = []
    for r in _jsonl(pdir / "proposals.jsonl"):
        text = f"Job: {r.get('job_title', '')}\n{r.get('job_summary', '')}\n\nProposal:\n{r['proposal_text']}"
        cited = r.get("cited_project_ids") or []
        out.append(Document(
            item_id=r["item_id"], type="proposal", title=f"Past proposal: {r.get('job_title', '')}", text=text,
            owner=owner, project_id=cited[0] if cited else None, date=r.get("date"),
            client_industry=r.get("client_industry"), outcome=r.get("outcome"),
            source=f"data/personas/{owner}/proposals.jsonl", skills=tag_skills(r["proposal_text"]),
        ))
    return out


def load_persona(persona_id: str, persona_dir: Path = PERSONA_DIR) -> list[Document]:
    pdir = persona_dir / persona_id
    docs: list[Document] = []
    for loader in (load_cv, load_case_studies, load_repos, load_reviews, load_proposals):
        docs.extend(loader(pdir, persona_id))
    return docs


def load_upload(owner: str, item_id: str, title: str, text: str, kind: str = "upload", **meta) -> Document:
    """A portfolio item the user adds in the UI (incremental re-index)."""
    return Document(item_id=item_id, type=kind, title=title, text=text, owner=owner, source="upload",
                    skills=tag_skills(text), **meta)


def list_personas(persona_dir: Path = PERSONA_DIR) -> list[str]:
    return sorted(p.name for p in persona_dir.glob("*") if (p / "profile.json").exists())
