"""Sign-in, onboarding, settings, memory viewer and portfolio management."""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, HTTPException

from agent import db, settings
from apps.api.auth.users import (CurrentUser, check_password, create_user, session_token,
                                 store_marketplace_token)
from apps.api.schemas import (ConnectedAccount, LoginIn, MemoryItem, MemoryOut, OnboardingIn, PersonaOut,
                              PortfolioItemOut, RegisterIn, SavedSearchIn, SavedSearchOut, SettingsIn,
                              SettingsOut, TokenOut, UploadIn, UserOut)
from rag.ingest.loaders import PERSONA_DIR, list_personas, load_persona

router = APIRouter(prefix="/api", tags=["auth"])


def _user_out(u: dict) -> UserOut:
    return UserOut(id=u["id"], email=u["email"], name=u["name"], persona_id=u.get("persona_id"),
                   onboarded=bool(u.get("persona_id")))


@router.post("/auth/register", response_model=TokenOut)
async def register(body: RegisterIn) -> TokenOut:
    if await db.fetchone("select 1 from users where email=%s", body.email.lower()):
        raise HTTPException(409, "email already registered")
    user = await create_user(body.email, body.password, body.name)
    return TokenOut(token=session_token(user["id"]), user=_user_out(user))


@router.post("/auth/login", response_model=TokenOut)
async def login(body: LoginIn) -> TokenOut:
    user = await db.fetchone("select * from users where email=%s", body.email.lower())
    if not user or not check_password(body.password, user["password_hash"]):
        raise HTTPException(401, "wrong email or password")
    return TokenOut(token=session_token(user["id"]), user=_user_out(user))


@router.get("/auth/me", response_model=UserOut)
async def me(user: dict = CurrentUser) -> UserOut:
    return _user_out(user)


@router.get("/personas", response_model=list[PersonaOut])
async def personas() -> list[PersonaOut]:
    out = []
    for pid in list_personas():
        p = json.loads((PERSONA_DIR / pid / "profile.json").read_text(encoding="utf-8"))
        out.append(PersonaOut(id=pid, name=p.get("name", pid), headline=p.get("headline", ""),
                              skills=p.get("skills", [])[:12], hourly_rate_usd=p.get("hourly_rate_usd", 0),
                              min_project_usd=p.get("min_project_usd", 0),
                              weekly_connects_budget=p.get("weekly_connects_budget", 80)))
    return out


@router.post("/onboarding", response_model=UserOut)
async def onboarding(body: OnboardingIn, user: dict = CurrentUser) -> UserOut:
    if body.persona_id not in list_personas():
        raise HTTPException(400, "unknown persona")
    await db.execute("update users set persona_id=%s where id=%s", body.persona_id, user["id"])
    data = {"hourly_rate_usd": body.hourly_rate_usd, "min_project_usd": body.min_project_usd,
            "weekly_connects_budget": body.weekly_connects_budget, "marketplace": body.marketplace}
    await db.execute("insert into user_settings(user_id, data) values (%s,%s) on conflict (user_id) do update"
                     " set data = user_settings.data || excluded.data, updated_at=now()", user["id"], db.jsonb(data))
    if body.marketplace == "gigsim":
        # GigSim dev accounts map one-to-one to personas; the token is stored encrypted like any other.
        await store_marketplace_token(user["id"], "gigsim", body.persona_id, f"gs-{body.persona_id}-dev")
    if body.saved_search:
        await add_search(body.saved_search, user)
    elif not await db.fetchone("select 1 from saved_searches where user_id=%s", user["id"]):
        await add_search(SavedSearchIn(name="All new jobs", query=""), user)
    u = await db.fetchone("select id, email, name, persona_id from users where id=%s", user["id"])
    return _user_out(u)


async def _settings(user_id: str) -> SettingsOut:
    row = await db.fetchone("select data from user_settings where user_id=%s", user_id)
    data = (row or {}).get("data") or {}
    searches = await db.fetch("select * from saved_searches where user_id=%s order by id", user_id)
    accounts = await db.fetch("select mode, account_id, created_at from marketplace_accounts where user_id=%s", user_id)
    return SettingsOut(
        autonomy=data.get("autonomy", settings.get("autonomy.default", "suggest")),
        hourly_rate_usd=data.get("hourly_rate_usd"), min_project_usd=data.get("min_project_usd"),
        weekly_connects_budget=data.get("weekly_connects_budget"), hidden_items=data.get("hidden_items", []),
        saved_searches=[SavedSearchOut(id=s["id"], name=s["name"], query=s["query"],
                                       category=(s["filters"] or {}).get("category"),
                                       interval_minutes=s["interval_minutes"],
                                       last_run_at=s["last_run_at"].isoformat() if s["last_run_at"] else None,
                                       enabled=s["enabled"]) for s in searches],
        connected_accounts=[ConnectedAccount(mode=a["mode"], account_id=a["account_id"],
                                             connected_at=a["created_at"].isoformat()) for a in accounts],
        model_profile=settings.config()["profile"], marketplace_mode=settings.get("marketplace.mode"),
        policy_version=int(settings.get("policy.version", 1)), rag_variant=settings.get("rag.variant", ""),
    )


@router.get("/settings", response_model=SettingsOut)
async def get_settings(user: dict = CurrentUser) -> SettingsOut:
    return await _settings(user["id"])


@router.put("/settings", response_model=SettingsOut)
async def put_settings(body: SettingsIn, user: dict = CurrentUser) -> SettingsOut:
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    await db.execute("update user_settings set data = data || %s, updated_at=now() where user_id=%s",
                     db.jsonb(patch), user["id"])
    return await _settings(user["id"])


@router.post("/settings/searches", response_model=SavedSearchOut)
async def add_search(body: SavedSearchIn, user: dict = CurrentUser) -> SavedSearchOut:
    row = await db.fetchone("insert into saved_searches(user_id, name, query, filters, interval_minutes)"
                            " values (%s,%s,%s,%s,%s) returning *", user["id"], body.name, body.query,
                            db.jsonb({"category": body.category} if body.category else {}), body.interval_minutes)
    return SavedSearchOut(id=row["id"], name=row["name"], query=row["query"], category=body.category,
                          interval_minutes=row["interval_minutes"])


@router.delete("/settings/searches/{search_id}", status_code=204)
async def delete_search(search_id: int, user: dict = CurrentUser) -> None:
    await db.execute("delete from saved_searches where id=%s and user_id=%s", search_id, user["id"])


# ----------------------------------------------------------------------------- memory viewer
RULE = ("Style rules are promoted only when the same edit pattern appears in at least "
        f"{settings.get('memory.style.promote_after')} of your last {settings.get('memory.style.window')} edits. "
        f"Outcome insights need at least {settings.get('memory.outcome.min_outcomes')} finished proposals in a category.")


@router.get("/memory", response_model=MemoryOut)
async def memory(user: dict = CurrentUser) -> MemoryOut:
    from agent import runner
    from agent.memory.store import list_memory

    store = (await runner.graphs())["store"]
    mem = await list_memory(user["id"], store)
    return MemoryOut(
        style=[MemoryItem(key=m["key"], kind="style", text=m["rule"], support=m.get("support"), detail=m)
               for m in mem["style"]],
        outcome=[MemoryItem(key=m["key"], kind="outcome", text=" ".join(m.get("insights", [])), support=m.get("n"),
                            detail=m) for m in mem["outcome"]],
        pending_edits=mem["pending_edits"], promotion_rule=RULE)


@router.delete("/memory/{kind}/{key}", status_code=204)
async def forget(kind: str, key: str, user: dict = CurrentUser) -> None:
    from agent import runner
    from agent.memory.store import delete_memory

    if kind not in ("style", "outcome"):
        raise HTTPException(400, "kind must be style or outcome")
    await delete_memory(user["id"], kind, key, (await runner.graphs())["store"])


# ----------------------------------------------------------------------------- portfolio
@router.get("/portfolio/items", response_model=list[PortfolioItemOut])
async def portfolio_items(user: dict = CurrentUser) -> list[PortfolioItemOut]:
    row = await db.fetchone("select data from user_settings where user_id=%s", user["id"])
    hidden = set(((row or {}).get("data") or {}).get("hidden_items", []))
    items = [PortfolioItemOut(item_id=d.item_id, type=d.type, title=d.title, date=d.date, hidden=d.item_id in hidden)
             for d in load_persona(user.get("persona_id") or "ai_ml")]
    for u in await db.fetch("select * from uploads where user_id=%s order by created_at", user["id"]):
        items.append(PortfolioItemOut(item_id=u["item_id"], type=u["kind"], title=u["title"],
                                      date=u["created_at"].date().isoformat(), hidden=u["item_id"] in hidden))
    return items


@router.post("/portfolio/items/{item_id}/hide", response_model=SettingsOut)
async def hide_item(item_id: str, user: dict = CurrentUser) -> SettingsOut:
    """'Delete' evidence: it is excluded from every search from now on (viva question 3)."""
    cur = await _settings(user["id"])
    hidden = sorted(set(cur.hidden_items) | {item_id})
    await db.execute("update user_settings set data = data || %s where user_id=%s",
                     db.jsonb({"hidden_items": hidden}), user["id"])
    return await _settings(user["id"])


@router.post("/portfolio/items/{item_id}/unhide", response_model=SettingsOut)
async def unhide_item(item_id: str, user: dict = CurrentUser) -> SettingsOut:
    cur = await _settings(user["id"])
    hidden = [i for i in cur.hidden_items if i != item_id]
    await db.execute("update user_settings set data = data || %s where user_id=%s",
                     db.jsonb({"hidden_items": hidden}), user["id"])
    return await _settings(user["id"])


@router.post("/portfolio/upload", response_model=PortfolioItemOut)
async def upload(body: UploadIn, user: dict = CurrentUser) -> PortfolioItemOut:
    """Add work in the UI; the persona index is re-built incrementally with the new item."""
    from rag.index import store as index_store
    from rag.index.build import build_chunks
    from rag.ingest.loaders import load_upload

    owner = user["id"]  # uploads live in the user's own index (tenant-scoped), never the shared persona one
    item_id = f"{owner}-up-{uuid.uuid4().hex[:6]}"
    await db.execute("insert into uploads(user_id, item_id, kind, title, text) values (%s,%s,%s,%s,%s)",
                     owner, item_id, body.kind, body.title, body.text)
    doc = load_upload(owner, item_id, body.title, body.text, kind=body.kind)
    for flavour in ("plain", "multivector", "contextual"):
        if index_store.is_cached(owner, flavour):
            index_store.get_index(owner, flavour).add(build_chunks(owner, flavour, docs=[doc]))
    return PortfolioItemOut(item_id=item_id, type=body.kind, title=body.title)
