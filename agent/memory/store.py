"""Long-term memory on a LangGraph store (Postgres in production, in-memory in tests).

Namespaces
  ("style", user)            promoted style rules       {rule, feature, support, promoted_at}
  ("style_window", user)     last N edit feature sets   (candidates, not used by the writer)
  ("outcome", user)          promoted insights per category {insights, n, promoted_at}
Only `record_edit` and `refresh_outcomes` write here, and only through promotion_rules."""
from __future__ import annotations

import time
from typing import Any

from langgraph.store.base import BaseStore

from agent import settings
from agent.memory import promotion_rules as rules

_fallback: BaseStore | None = None


def _store(store: BaseStore | None = None) -> BaseStore | None:
    if store is not None:
        return store
    try:
        from langgraph.config import get_store

        return get_store()
    except Exception:  # noqa: BLE001 - outside a graph run
        return _fallback


def set_fallback(store: BaseStore) -> None:
    global _fallback
    _fallback = store


async def style_rules(user_id: str, store: BaseStore | None = None) -> list[str]:
    st = _store(store)
    if st is None or not user_id:
        return []
    items = await st.asearch(("style", user_id), limit=50)
    return [i.value["rule"] for i in sorted(items, key=lambda i: i.value.get("promoted_at", 0))]


async def list_memory(user_id: str, store: BaseStore) -> dict[str, list[dict]]:
    style = await store.asearch(("style", user_id), limit=100)
    outcome = await store.asearch(("outcome", user_id), limit=100)
    window = await store.aget(("style_window", user_id), "window")
    return {
        "style": [{"key": i.key, **i.value} for i in style],
        "outcome": [{"key": i.key, **i.value} for i in outcome],
        "pending_edits": (window.value.get("edits", []) if window else []),
    }


async def delete_memory(user_id: str, kind: str, key: str, store: BaseStore) -> None:
    await store.adelete((kind, user_id), key)
    if kind == "style":
        # Forget the evidence too, so the same edits do not re-promote it immediately.
        window = await store.aget(("style_window", user_id), "window")
        if window:
            edits = [[f for f in feats if f != key] for feats in window.value.get("edits", [])]
            await store.aput(("style_window", user_id), "window", {"edits": edits})


async def record_edit(user_id: str, original: str, edited: str, store: BaseStore | None = None) -> dict[str, Any]:
    """Apply the style promotion rule to one user edit. Returns what changed."""
    st = _store(store)
    if st is None:
        return {"features": [], "promoted": []}
    cfg = settings.get("memory.style")
    feats = rules.edit_features(original, edited)
    window_item = await st.aget(("style_window", user_id), "window")
    edits = (window_item.value.get("edits", []) if window_item else []) + [feats]
    edits = edits[-int(cfg["window"]):]
    await st.aput(("style_window", user_id), "window", {"edits": edits})
    promoted = []
    for feature, support in rules.promote_style(edits, int(cfg["promote_after"])).items():
        existing = await st.aget(("style", user_id), feature)
        if existing is None:
            promoted.append(feature)
        await st.aput(("style", user_id), feature, {
            "rule": rules.rule_text(feature), "feature": feature, "support": support,
            "window": len(edits), "promoted_at": existing.value["promoted_at"] if existing else time.time(),
        })
    return {"features": feats, "promoted": promoted}


async def outcome_insights(user_id: str, category: str, store: BaseStore | None = None) -> list[str]:
    st = _store(store)
    if st is None or not user_id or not category:
        return []
    item = await st.aget(("outcome", user_id), category.lower())
    return item.value.get("insights", []) if item else []


async def refresh_outcomes(user_id: str, category: str, rows: list[dict], store: BaseStore | None = None) -> list[str]:
    st = _store(store)
    if st is None:
        return []
    insights = rules.outcome_insights(rows, int(settings.get("memory.outcome.min_outcomes", 3)))
    if insights:
        await st.aput(("outcome", user_id), category.lower(),
                      {"insights": insights, "n": len(rows), "category": category, "promoted_at": time.time()})
    return insights
