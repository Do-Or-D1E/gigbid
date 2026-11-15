"""Portfolio tool implementations (pure functions, called by the MCP server and tests).
Read-only: they never change the portfolio."""
from __future__ import annotations

import json
from collections import Counter
from typing import Literal

from pydantic import BaseModel, Field

from rag.ingest.loaders import PERSONA_DIR, Document, load_persona
from rag.retriever import RetrievalQuery, get_pipeline

ItemType = Literal["cv", "case_study", "repo", "review", "proposal", "upload"]


class EvidenceFilters(BaseModel):
    types: list[ItemType] | None = Field(default=None, description="Only these item types")
    outcome: list[Literal["won", "replied", "ignored"]] | None = Field(
        default=None, description="Past proposals with these outcomes only")
    since: str | None = Field(default=None, pattern=r"^\d{4}(-\d{2})?$", description="Earliest date, YYYY or YYYY-MM")
    exclude_items: list[str] | None = Field(default=None, description="Item ids to leave out")


class Evidence(BaseModel):
    item_id: str
    type: str
    title: str
    snippet: str
    source: str
    date: str | None = None
    outcome: str | None = None
    project_id: str | None = None
    rank: int


class EvidenceResults(BaseModel):
    requirement: str
    owner: str
    variant: str
    items: list[Evidence]


class CaseStudy(BaseModel):
    item_id: str
    type: str
    title: str
    text: str
    project_id: str | None = None
    date: str | None = None
    client_industry: str | None = None
    skills: list[str] = Field(default_factory=list)
    source: str


class SkillCount(BaseModel):
    skill: str
    items: int


class SkillList(BaseModel):
    owner: str
    profile_skills: list[str]
    evidenced_skills: list[SkillCount]


_docs_cache: dict[str, dict[str, Document]] = {}


def _docs(owner: str) -> dict[str, Document]:
    if owner not in _docs_cache:
        _docs_cache[owner] = {d.item_id: d for d in load_persona(owner)}
    return _docs_cache[owner]


def hidden_items(user_id: str | None) -> set[str]:
    """Evidence the user deleted in the UI is excluded from every search."""
    from agent import settings

    if not user_id or not settings.database_url():
        return set()
    from agent import db

    with db.connect() as conn:
        row = conn.execute("select data from user_settings where user_id=%s", (user_id,)).fetchone()
    return set((row or {}).get("data", {}).get("hidden_items", [])) if row else set()


def has_uploads(user_id: str) -> bool:
    from agent import settings

    if not settings.database_url() or user_id.startswith("local:"):
        return False
    from agent import db

    with db.connect() as conn:
        return conn.execute("select 1 from uploads where user_id=%s limit 1", (user_id,)).fetchone() is not None


async def search_evidence(owner: str, requirement: str, k: int = 5, filters: EvidenceFilters | None = None,
                          user_id: str | None = None) -> EvidenceResults:
    filters = filters or EvidenceFilters()
    exclude = set(filters.exclude_items or []) | hidden_items(user_id)
    pipe = get_pipeline()
    owners = [owner] + ([user_id] if user_id and has_uploads(user_id) else [])
    ranked: list = []
    for o in owners:
        q = RetrievalQuery(owner=o, title=requirement, description="", requirements=[requirement],
                           types=list(filters.types) if filters.types else None, exclude_items=exclude or None)
        res = await pipe.retrieve(q, k=max(k * 3, 10))
        ranked.append(res.items)
    # Interleave persona and upload results by rank so new uploads can surface.
    merged = [it for group in zip(*[r + [None] * (max(map(len, ranked)) - len(r)) for r in ranked])
              for it in group if it is not None]
    items = []
    for it in merged:
        if filters.outcome and it.outcome not in filters.outcome:
            continue
        if filters.since and (it.date or "") < filters.since:
            continue
        items.append(Evidence(item_id=it.item_id, type=it.type, title=it.title, snippet=it.snippet[:600],
                              source=it.source, date=it.date, outcome=it.outcome, project_id=it.project_id,
                              rank=len(items) + 1))
        if len(items) >= k:
            break
    return EvidenceResults(requirement=requirement, owner=owner, variant=pipe.cfg.name, items=items)


def get_case_study(owner: str, item_id: str, user_id: str | None = None) -> CaseStudy:
    doc = _docs(owner).get(item_id)
    if doc is None and user_id and "-up-" in item_id:
        from rag.index.build import user_upload_docs

        doc = next((d for d in user_upload_docs(user_id) if d.item_id == item_id), None)
    if doc is None:
        raise KeyError(f"no portfolio item {item_id!r}")
    return CaseStudy(item_id=doc.item_id, type=doc.type, title=doc.title, text=doc.text[:12000],
                     project_id=doc.project_id, date=doc.date, client_industry=doc.client_industry,
                     skills=doc.skills, source=doc.source)


def list_skills(owner: str) -> SkillList:
    profile_path = PERSONA_DIR / owner / "profile.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8")) if profile_path.exists() else {}
    counts: Counter = Counter()
    for d in _docs(owner).values():
        if d.type != "proposal":
            counts.update(set(d.skills))
    return SkillList(owner=owner, profile_skills=profile.get("skills", []),
                     evidenced_skills=[SkillCount(skill=s, items=n) for s, n in counts.most_common()])
