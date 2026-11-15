"""Client Liaison nodes for the conversation graph: read the thread, classify intent
(question, negotiation, interview request, scam signal), gather slots or evidence, draft a
reply, check it, and stop for approval before anything is sent."""
from __future__ import annotations

import hashlib
import json
import re

from langgraph.types import interrupt

from agent import guardrails, llm
from agent.handoffs import ApprovalDecision, MessageIntent, ReplyDraft
from agent.memory.store import record_edit
from agent.nodes._base import gateway, node
from agent.nodes.compliance import check_text
from agent.prompts import load_prompt

OFF_PLATFORM = re.compile(r"(telegram|whats\s?app|wa\.me|skype|signal|wechat|gmail|outlook|my email|"
                          r"pay (?:you )?(?:outside|directly|via (?:paypal|crypto|bitcoin|usdt|wire))|"
                          r"(?:registration|training|equipment|processing) fee|send .{0,20}(?:free|unpaid) (?:sample|test))",
                          re.I)


def _key(*parts: str) -> str:
    return "gb-" + hashlib.sha256(":".join(parts).encode()).hexdigest()[:24]


@node("liaison_read")
async def liaison_read(state: dict, config: dict) -> dict:
    msgs = await gateway(config).call("list_messages", {"thread_id": state["thread_id"]})
    messages = msgs.get("messages", [])
    client_msgs = [m for m in messages if (m.get("sender") or m.get("from")) not in ("freelancer", "me", "you")]
    last = client_msgs[-1] if client_msgs else (messages[-1] if messages else {})
    hits = guardrails.detect_injection(last.get("text", ""))
    return {"messages": messages[-12:], "last_client_message": last, "injection_hits": hits, "status": "reading"}


@node("intent")
async def classify_intent(state: dict, config: dict) -> dict:
    last = state.get("last_client_message") or {}
    history = "\n".join(f"{m.get('sender', '?')}: {m.get('text', '')[:300]}" for m in state.get("messages", [])[-6:])
    user = f"Recent thread:\n{guardrails.untrusted('client_message', history)}"
    intent, _ = await llm.call("intent", load_prompt("liaison_intent"), user, MessageIntent, temperature=0)
    if OFF_PLATFORM.search(last.get("text", "")):
        intent.intent = "scam_signal"
        intent.summary = (intent.summary + " (off-platform or fee request detected)").strip()
    return {"intent": intent.model_dump()}


@node("liaison_gather")
async def gather(state: dict, config: dict) -> dict:
    gw = gateway(config)
    intent = state.get("intent") or {}
    out: dict = {}
    if intent.get("intent") == "interview_request" or intent.get("asks_for_times"):
        slots = await gw.call("free_slots", {"days": 5, "max_slots": 3})
        out["slots"] = slots.get("slots", [])
    if intent.get("intent") in ("question", "negotiation"):
        q = (state.get("last_client_message") or {}).get("text", "")[:250] or "relevant experience"
        res = await gw.call("search_evidence", {"requirement": q, "k": 3})
        out["evidence"] = res.get("items", [])
    return out


@node("liaison")
async def draft_reply(state: dict, config: dict) -> dict:
    intent = state.get("intent") or {}
    profile = state.get("profile") or {}
    history = "\n".join(f"{m.get('sender', '?')}: {m.get('text', '')[:400]}" for m in state.get("messages", [])[-6:])
    ev = "\n".join(f'<evidence id="{e["item_id"]}">{e.get("snippet", "")[:350]}</evidence>'
                   for e in state.get("evidence", []))
    user = (f"Intent: {json.dumps(intent)}\nFree slots: {json.dumps([s.get('label') for s in state.get('slots', [])])}\n"
            f"Freelancer floor: hourly ${profile.get('hourly_rate_usd')}, minimum project ${profile.get('min_project_usd')}\n\n"
            f"{guardrails.untrusted('client_message', history)}\n\n{ev}")
    reply, _ = await llm.call("liaison", load_prompt("liaison_reply"), user, ReplyDraft, temperature=0.3)
    if state.get("slots") and not reply.proposed_slots:
        reply.proposed_slots = [s["label"] for s in state["slots"]]
    return {"reply": reply.model_dump(), "status": "drafted"}


@node("message_compliance")
async def message_compliance(state: dict, config: dict) -> dict:
    reply = dict(state["reply"])
    verdict = await check_text(reply["text"], json.dumps({"intent": (state.get("intent") or {}).get("intent")}))
    if verdict.verdict == "block":
        return {"compliance": verdict.model_dump(), "status": "blocked",
                "attention": f"Compliance Guard blocked this reply: {verdict.reason}"}
    reply["text"] = verdict.cleaned_cover_letter or reply["text"]
    return {"compliance": verdict.model_dump(), "reply": reply, "status": "compliant"}


@node("message_approval")
async def message_approval(state: dict, config: dict) -> dict:
    gw = gateway(config)
    prev = await gw.call("send_message", {"thread_id": state["thread_id"], "text": state["reply"]["text"],
                                          "idempotency_key": _key(state.get("run_id", ""), "preview"),
                                          "dry_run": True})
    payload = {"kind": "message", "thread_id": state["thread_id"], "job_id": state.get("job_id"),
               "intent": state.get("intent"), "reply": state["reply"], "slots": state.get("slots", []),
               "client_message": state.get("last_client_message"), "compliance": state.get("compliance"),
               "injection_hits": state.get("injection_hits", []), "preview": prev.get("preview")}
    decision = ApprovalDecision.model_validate(interrupt(payload))
    out: dict = {"approval": decision.model_dump(), "preview": prev.get("preview")}
    if decision.action == "reject":
        out["status"] = "rejected"
    elif decision.action == "edit":
        original = state["reply"]["text"]
        edited = decision.edited_cover_letter or original
        mem = await record_edit(state.get("user_id", ""), original, edited)
        out["reply"] = {**state["reply"], "text": edited}
        out["edits"] = [{"features": mem["features"], "promoted": mem["promoted"]}]
        out["status"] = "edited"
    else:
        out["status"] = "approved"
    return out


def route_after_message_approval(state: dict) -> str:
    return {"approved": "send", "edited": "message_compliance"}.get(state.get("status", ""), "end")


@node("send")
async def send(state: dict, config: dict) -> dict:
    gw = gateway(config)
    reply = state["reply"]
    content = hashlib.sha256(reply["text"].encode()).hexdigest()[:12]
    sent = await gw.call("send_message", {"thread_id": state["thread_id"], "text": reply["text"],
                                          "idempotency_key": _key(state["thread_id"], "msg", content)})
    holds = []
    if reply.get("create_hold") and state.get("slots"):
        for slot in state["slots"][: len(reply.get("proposed_slots") or state["slots"])]:
            holds.append(await gw.call("create_interview_hold", {
                "start": slot["start"], "title": f"Client interview ({state['thread_id']})",
                "idempotency_key": _key(state["thread_id"], "hold", slot["start"])}))
    return {"sent": {"message": sent, "holds": holds}, "status": "sent"}
