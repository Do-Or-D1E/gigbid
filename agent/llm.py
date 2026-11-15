"""Model router. Every node asks for a model by node name; the profile in config decides
which provider/model serves it. Handles structured output, fallback on rate limits or
errors, a persistent hard cap on billed spend, an eval cache, and usage accounting."""
from __future__ import annotations

import asyncio
import contextvars
import hashlib
import json
import os
import sqlite3
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, TypeVar

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from agent import settings

T = TypeVar("T", bound=BaseModel)


class BudgetExceeded(RuntimeError):
    """Raised before a billed call that would break the hard spend cap."""


@dataclass
class ModelSpec:
    provider: str
    model: str
    base_url: str
    api_key: str
    billed: bool
    structured_method: str
    price_in: float
    price_out: float
    extra: dict = field(default_factory=dict)


@dataclass
class Usage:
    node: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    billed_usd: float = 0.0
    list_usd: float = 0.0
    latency_s: float = 0.0
    cached: bool = False
    fallback: bool = False
    error: str | None = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


# Collected usage for the current run (set by the executor / eval harness).
usage_sink: contextvars.ContextVar[list[Usage] | None] = contextvars.ContextVar("usage_sink", default=None)


def _record(u: Usage) -> None:
    sink = usage_sink.get()
    if sink is not None:
        sink.append(u)
    if u.billed_usd > 0:
        ledger().add(u)
    from agent import tracing

    tracing.add(tracing.Span("llm", u.node, node=tracing.current_node.get() or u.node, model=u.model,
                             input_tokens=u.input_tokens, output_tokens=u.output_tokens, usd=u.billed_usd,
                             list_usd=u.list_usd, latency_s=u.latency_s, error=u.error,
                             result={"cached": u.cached, "fallback": u.fallback}))


# --------------------------------------------------------------------------- ledger
class Ledger:
    """Persistent record of billed spend. Writes go to a local SQLite file, or to Postgres when
    GIGBID_LEDGER_PG=1 (the deployment). total() sums every ledger it can see, so the hard cap
    covers evals, local runs and the deployment together."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pg = settings.database_url() if os.environ.get("GIGBID_LEDGER_PG") == "1" else None
        path = settings.ROOT / "cache" / "ledger.sqlite"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            path = __import__("pathlib").Path("/tmp/gigbid_ledger.sqlite")
        self._path = str(path)
        with sqlite3.connect(self._path) as conn:
            conn.execute("create table if not exists llm_ledger (id integer primary key, ts real, node text, model text,"
                         " input_tokens int, output_tokens int, usd real)")
        if self._pg:
            import psycopg

            with psycopg.connect(self._pg, autocommit=True) as conn:
                conn.execute("create table if not exists llm_ledger (id bigserial primary key, ts timestamptz default now(),"
                             " node text, model text, input_tokens int, output_tokens int, usd double precision)")

    def add(self, u: Usage) -> None:
        with self._lock:
            if self._pg:
                import psycopg

                with psycopg.connect(self._pg, autocommit=True) as conn:
                    conn.execute("insert into llm_ledger(node, model, input_tokens, output_tokens, usd) values (%s,%s,%s,%s,%s)",
                                 (u.node, u.model, u.input_tokens, u.output_tokens, u.billed_usd))
            else:
                with sqlite3.connect(self._path) as conn:
                    conn.execute("insert into llm_ledger(ts,node,model,input_tokens,output_tokens,usd) values (?,?,?,?,?,?)",
                                 (time.time(), u.node, u.model, u.input_tokens, u.output_tokens, u.billed_usd))

    def total(self) -> float:
        extra = float(os.environ.get("GIGBID_EXTERNAL_SPEND_USD", "0") or 0)
        with sqlite3.connect(self._path) as conn:
            local = float(conn.execute("select coalesce(sum(usd),0) from llm_ledger").fetchone()[0])
        pg = 0.0
        url = settings.database_url()
        if url:
            try:
                import psycopg

                with psycopg.connect(url, connect_timeout=5) as conn:
                    row = conn.execute("select coalesce(sum(usd),0) from llm_ledger").fetchone()
                pg = float(row[0])
            except Exception:  # noqa: BLE001 - no table / no server: nothing billed there
                pg = 0.0
        return local + pg + extra


_ledger: Ledger | None = None


def ledger() -> Ledger:
    global _ledger
    if _ledger is None:
        _ledger = Ledger()
    return _ledger


# --------------------------------------------------------------------------- cache
class _Cache:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        with sqlite3.connect(self.path) as conn:
            conn.execute("create table if not exists cache (k text primary key, v text)")

    def get(self, key: str) -> dict | None:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute("select v from cache where k=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key: str, value: dict) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute("insert or replace into cache(k, v) values (?, ?)", (key, json.dumps(value)))


_cache: _Cache | None = None


def _get_cache() -> _Cache | None:
    global _cache
    if os.environ.get("GIGBID_LLM_CACHE") != "1":
        return None
    if _cache is None:
        _cache = _Cache(settings.ROOT / settings.get("llm.cache_path", "cache/llm_cache.sqlite"))
    return _cache


# --------------------------------------------------------------------------- routing
def _spec(tier_cfg: dict) -> ModelSpec:
    prov = settings.get(f"providers.{tier_cfg['provider']}")
    price = settings.get("prices", {}).get(tier_cfg["model"], [0.0, 0.0])
    return ModelSpec(
        provider=tier_cfg["provider"],
        model=tier_cfg["model"],
        base_url=os.environ.get(prov.get("base_url_env", ""), "") or prov["base_url"],
        api_key=os.environ.get(prov["api_key_env"], "") or ("ollama" if tier_cfg["provider"] == "ollama" else ""),
        billed=bool(prov.get("billed", True)),
        structured_method=prov.get("structured_method", "json_schema"),
        price_in=price[0],
        price_out=price[1],
        extra=dict(tier_cfg.get("extra", {})),
    )


def spec_for(node: str, *, fallback: bool = False, profile: str | None = None) -> ModelSpec:
    profile = profile or settings.config()["profile"]
    tier = settings.get("nodes", {}).get(node, "small")
    prof = settings.get(f"profiles.{profile}")
    if prof is None:
        raise KeyError(f"unknown model profile {profile!r}")
    tier_cfg = (prof["fallback"] if fallback else prof["tiers"])[tier]
    return _spec(tier_cfg)


def chat_model(node: str, *, fallback: bool = False, profile: str | None = None, **kw: Any) -> ChatOpenAI:
    s = spec_for(node, fallback=fallback, profile=profile)
    params: dict[str, Any] = dict(
        model=s.model,
        base_url=s.base_url,
        api_key=s.api_key or "missing-key",
        temperature=kw.pop("temperature", settings.get("llm.temperature", 0.2)),
        timeout=settings.get("llm.timeout_s", 45),
        max_retries=settings.get("llm.max_retries", 2),
        max_tokens=kw.pop("max_tokens", settings.get("llm.max_output_tokens", 1800)),
    )
    if "gpt-oss" in s.model:
        params["reasoning_effort"] = kw.pop("reasoning_effort", "low")
    params.update(kw)
    return ChatOpenAI(**params)


def _cost(s: ModelSpec, tin: int, tout: int) -> float:
    return (tin * s.price_in + tout * s.price_out) / 1_000_000


def _check_budget(s: ModelSpec, est_in: int) -> None:
    if not s.billed:
        return
    cap = float(settings.get("llm.billed_cap_usd", 2.0))
    spent = ledger().total()
    if spent + _cost(s, est_in, 800) > cap:
        raise BudgetExceeded(f"billed spend {spent:.4f} USD would exceed cap {cap:.2f} USD")


def _messages(system: str, user: str | list[BaseMessage]) -> list[BaseMessage]:
    if isinstance(user, list):
        return [SystemMessage(system), *user]
    return [SystemMessage(system), HumanMessage(user)]


def _key(s: ModelSpec, msgs: list[BaseMessage], schema: type[BaseModel] | None, temp: float) -> str:
    payload = {
        "m": s.model,
        "msgs": [(m.type, m.content) for m in msgs],
        "schema": schema.model_json_schema() if schema else None,
        "t": temp,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def _is_retryable(exc: Exception) -> bool:
    text = f"{type(exc).__name__} {exc}".lower()
    return any(t in text for t in ("rate", "429", "timeout", "503", "502", "500", "overloaded", "connection",
                                   "json", "validation", "parse", "tool_use_failed", "413", "too large"))


async def _invoke_once(node: str, s: ModelSpec, msgs, schema, *, fallback: bool, temperature: float | None):
    temp = settings.get("llm.temperature", 0.2) if temperature is None else temperature
    cache = _get_cache()
    key = _key(s, msgs, schema, temp) if cache else ""
    if cache:
        hit = cache.get(key)
        if hit is not None:
            u = Usage(node, s.provider, s.model, hit["in"], hit["out"], 0.0, _cost(s, hit["in"], hit["out"]),
                      0.0, cached=True, fallback=fallback)
            _record(u)
            if schema is not None:
                return schema.model_validate(hit["value"]), u
            return hit["value"], u

    est_in = sum(len(str(m.content)) for m in msgs) // 4
    _check_budget(s, est_in)
    model = chat_model(node, fallback=fallback, temperature=temp)
    t0 = time.perf_counter()
    if schema is not None:
        runnable = model.with_structured_output(schema, method=s.structured_method, include_raw=True)
        out = await runnable.ainvoke(msgs)
        raw, parsed, perr = out["raw"], out["parsed"], out.get("parsing_error")
        if parsed is None:
            raise ValueError(f"structured output parse failed: {perr}")
        value: Any = parsed
    else:
        raw = await model.ainvoke(msgs)
        value = raw.content
    latency = time.perf_counter() - t0
    meta = getattr(raw, "usage_metadata", None) or {}
    tin, tout = int(meta.get("input_tokens", 0)), int(meta.get("output_tokens", 0))
    u = Usage(node, s.provider, s.model, tin, tout, _cost(s, tin, tout) if s.billed else 0.0,
              _cost(s, tin, tout), latency, fallback=fallback)
    _record(u)
    if cache:
        cache.put(key, {"in": tin, "out": tout,
                        "value": value.model_dump(mode="json") if isinstance(value, BaseModel) else value})
    return value, u


async def call(node: str, system: str, user: str | list[BaseMessage], schema: type[T] | None = None,
               *, temperature: float | None = None, profile: str | None = None) -> tuple[Any, Usage]:
    """Run one model call for `node`. Tries the primary model, then the configured fallback."""
    msgs = _messages(system, user)
    last: Exception | None = None
    for fallback in (False, True):
        s = spec_for(node, fallback=fallback, profile=profile)
        for attempt in range(2):
            try:
                return await _invoke_once(node, s, msgs, schema, fallback=fallback, temperature=temperature)
            except BudgetExceeded:
                raise
            except Exception as exc:  # noqa: BLE001 - classify then retry or fall back
                last = exc
                _record(Usage(node, s.provider, s.model, error=f"{type(exc).__name__}: {str(exc)[:200]}",
                              fallback=fallback))
                if not _is_retryable(exc):
                    break
                await asyncio.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"{node}: all models failed: {last}") from last


def summarize(usages: list[Usage]) -> dict[str, Any]:
    return {
        "calls": len([u for u in usages if not u.error]),
        "errors": len([u for u in usages if u.error]),
        "input_tokens": sum(u.input_tokens for u in usages),
        "output_tokens": sum(u.output_tokens for u in usages),
        "billed_usd": round(sum(u.billed_usd for u in usages), 6),
        "list_usd": round(sum(u.list_usd for u in usages), 6),
        "fallbacks": len([u for u in usages if u.fallback and not u.error]),
        "cached": len([u for u in usages if u.cached]),
    }


def usage_dicts(usages: list[Usage]) -> list[dict]:
    return [asdict(u) for u in usages]
