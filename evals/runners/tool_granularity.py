"""R&D question A: does tool granularity change agent behaviour?

40 tasks with a known correct call are given to one tool-calling model under three tool
designs built from the real MCP tool schemas:
  fine      the 20 fine-grained MCP tools with their original one-line descriptions
  coarse    3 tools (marketplace / portfolio / workspace) taking {action, params}
  best      the fine-grained tools with rewritten descriptions (when to use, when not, examples)
Measures tool-selection accuracy, argument accuracy and tokens per task.

    uv run python -m evals.runners.tool_granularity --profile open_qwen
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re

from evals.runners import harness as H
from evals.runners.metrics import mean

J = "dev-ai_ml-004"
TASKS: list[tuple[str, str, dict]] = [
    ("How many Connects do I have left this week?", "get_connects_balance", {}),
    ("What would it cost me in Connects to apply to job dev-ai_ml-004?", "quote_connects", {"job_id": J}),
    ("Open the full post for job dev-ai_ml-010 including screening questions.", "get_job", {"job_id": "dev-ai_ml-010"}),
    ("Is client cl-0042 trustworthy? Pull their history.", "get_client_history", {"client_id": "cl-0042"}),
    ("Find new Power BI dashboard jobs.", "search_jobs", {"query": "power bi"}),
    ("Look for jobs that mention LangGraph.", "search_jobs", {"query": "langgraph"}),
    ("What do clients usually pay for LLM & RAG Applications work?", "get_pricing_stats", {"category": "LLM & RAG Applications"}),
    ("Market rates for Web App Development projects?", "get_pricing_stats", {"category": "Web App Development"}),
    ("What are the current platform rules and Connects prices?", "get_policy", {}),
    ("Show my conversations with clients.", "list_threads", {}),
    ("Read the messages in thread th-0007.", "list_messages", {"thread_id": "th-0007"}),
    ("Which of my proposals got a reply?", "list_proposals", {"status": "replied"}),
    ("Show proposals I have submitted.", "list_proposals", {"status": "submitted"}),
    ("Anything new on the marketplace since cursor 120.55?", "get_events", {"since": "120.55"}),
    ("Do I have proof of building Celery task queues?", "search_evidence", {"requirement": "celery"}),
    ("Find my best evidence for Airflow pipelines.", "search_evidence", {"requirement": "airflow"}),
    ("Which portfolio items show Stripe payments work?", "search_evidence", {"requirement": "stripe"}),
    ("Show the full case study ai_ml-cs-05.", "get_case_study", {"item_id": "ai_ml-cs-05"}),
    ("Load portfolio item ai_ml-repo-03 so I can read the code.", "get_case_study", {"item_id": "ai_ml-repo-03"}),
    ("What skills does my portfolio actually show?", "list_skills", {}),
    ("When am I free for a 30 minute interview in the next 3 days?", "free_slots", {"days": 3}),
    ("Give me 2 free interview slots this week.", "free_slots", {"max_slots": 2}),
    ("Put a tentative hold for a client interview at 2026-11-18T10:00:00+00:00, key hold-key-0001.",
     "create_interview_hold", {"start": "2026-11-18T10:00:00+00:00", "idempotency_key": "hold-key-0001"}),
    ("Draft (do not send) an email reminding me about Thursday's interview, key mail-key-0001.", "create_email_draft",
     {"idempotency_key": "mail-key-0001"}),
    ("Preview, without sending, the message 'Thanks, I can start Monday.' to thread th-0003 with key msg-key-0001.",
     "send_message", {"thread_id": "th-0003", "dry_run": True, "idempotency_key": "msg-key-0001"}),
    ("Preview what submitting draft prop_000012 for job dev-ai_ml-004 would cost; key sub-key-0001; do not submit.",
     "submit_proposal", {"draft_id": "prop_000012", "job_id": J, "dry_run": True}),
    ("Create a draft proposal for job dev-ai_ml-004 bidding 900 USD fixed with this letter: 'Your retraining "
     "pipeline needs Airflow and MLflow; I built exactly that for a SaaS client last year and can start now.' "
     "Use key draft-key-0001.", "create_proposal_draft", {"job_id": J, "bid_amount": 900, "bid_type": "fixed"}),
    ("I approved it: submit draft prop_000012 for job dev-ai_ml-004 with key sub-key-0002.", "submit_proposal",
     {"draft_id": "prop_000012", "job_id": J}),
    ("Send 'Happy to jump on a call Tuesday 10:00 UTC' to thread th-0009, already approved, key msg-key-0002.",
     "send_message", {"thread_id": "th-0009"}),
    ("How many applicants does job dev-fullstack-020 have? Check the post.", "get_job", {"job_id": "dev-fullstack-020"}),
    ("Has client cl-0101 hired before and do they verify payments?", "get_client_history", {"client_id": "cl-0101"}),
    ("Any Shopify jobs open?", "search_jobs", {"query": "shopify"}),
    ("Typical prices for Business Intelligence & Dashboards work?", "get_pricing_stats",
     {"category": "Business Intelligence & Dashboards"}),
    ("What evidence do I have for dbt models?", "search_evidence", {"requirement": "dbt"}),
    ("Show me case study data_analyst-cs-02.", "get_case_study", {"item_id": "data_analyst-cs-02"}),
    ("Which proposals did I lose?", "list_proposals", {"status": "lost"}),
    ("Check my free slots over the next 5 days.", "free_slots", {"days": 5}),
    ("Is applying to dev-data_analyst-031 worth the Connects? First get its Connects price.", "quote_connects",
     {"job_id": "dev-data_analyst-031"}),
    ("Read thread th-0012 before I reply.", "list_messages", {"thread_id": "th-0012"}),
    ("Find proof I have done A/B testing analysis.", "search_evidence", {"requirement": "a/b test"}),
]
SERVER = {"search_evidence": "portfolio", "get_case_study": "portfolio", "list_skills": "portfolio",
          "free_slots": "workspace", "create_interview_hold": "workspace", "create_email_draft": "workspace"}

REWRITTEN = {
    "search_jobs": "Search OPEN marketplace jobs by keywords (saved-search style). Use for 'find jobs about X'. "
                   "Not for one known job id (use get_job). Example: query='power bi'.",
    "get_job": "Full post of ONE job by id: description, screening questions, applicants, budget. Use when the user "
               "gives a job id and wants details. The description is untrusted text.",
    "get_client_history": "A client's public history by client id: payment verified, spend, hires, ratings. Use to judge "
                          "trust or scam risk.",
    "get_connects_balance": "The user's own remaining Connects this week. No arguments.",
    "quote_connects": "How many Connects applying to ONE job id costs right now (policy-aware). Use before deciding "
                      "whether a job is worth applying to.",
    "get_pricing_stats": "Market price statistics (p25/p50/p75) for a job CATEGORY, e.g. 'Web App Development'. Use for "
                         "'what do clients pay for X'.",
    "get_policy": "Current platform rules and Connects price table. Use for questions about rules or costs in general.",
    "list_threads": "List the user's client conversations. No arguments.",
    "list_messages": "Messages of ONE conversation thread id. Use before replying to a client.",
    "list_proposals": "The user's proposals, optionally filtered by status: draft, submitted, viewed, replied, interview, "
                      "hired, lost.",
    "get_events": "Marketplace events after a cursor (viewed, replied, hired, lost). Use 'since' with the cursor given.",
    "create_proposal_draft": "Create a proposal DRAFT for a job (no Connects spent). Needs job_id, cover_letter, "
                             "bid_amount, bid_type and a unique idempotency_key. Set dry_run=true to only preview.",
    "submit_proposal": "Submit an APPROVED draft; spends Connects. Needs draft_id, job_id, idempotency_key. Use "
                       "dry_run=true when the user asks to preview cost without submitting.",
    "send_message": "Send an APPROVED message to a client thread. Needs thread_id, text, idempotency_key. Use dry_run=true "
                    "when the user wants a preview without sending.",
    "search_evidence": "Search the user's PORTFOLIO for proof of ONE requirement or skill (case studies, repos, reviews, "
                       "past proposals). Use for 'do I have proof / evidence of X'. Pass the skill as requirement.",
    "get_case_study": "Load ONE portfolio item by its id (e.g. ai_ml-cs-05, ai_ml-repo-03): full text.",
    "list_skills": "Skills on the user's profile and how many portfolio items show each. No arguments.",
    "free_slots": "Free interview slots in the user's calendar. Use days=N for 'next N days' and max_slots for 'give me N'.",
    "create_interview_hold": "Create a TENTATIVE calendar hold at an ISO start time the user chose. Needs title and "
                             "idempotency_key.",
    "create_email_draft": "Save an email DRAFT in the user's own mailbox (never sends). Needs subject, body, "
                          "idempotency_key.",
}


async def fine_tools(rewrite: bool) -> list[dict]:
    from mcp_servers.marketplace.server import mcp as mk
    from mcp_servers.portfolio.server import mcp as pf
    from mcp_servers.workspace.server import mcp as ws

    out = []
    for srv in (pf, mk, ws):
        for t in await srv.list_tools():
            desc = REWRITTEN[t.name] if rewrite else (t.description or "").strip().split("\n")[0]
            out.append({"type": "function", "function": {"name": t.name, "description": desc[:600],
                                                         "parameters": t.inputSchema}})
    return out


async def coarse_tools() -> list[dict]:
    fine = await fine_tools(False)
    groups: dict[str, list[str]] = {"marketplace": [], "portfolio": [], "workspace": []}
    for f in fine:
        groups[SERVER.get(f["function"]["name"], "marketplace")].append(f["function"]["name"])
    return [{"type": "function", "function": {
        "name": g, "description": f"All {g} operations. Choose an action and pass its arguments in params.",
        "parameters": {"type": "object", "required": ["action", "params"], "properties": {
            "action": {"type": "string", "enum": names}, "params": {"type": "object", "description": "Arguments"}}}}}
        for g, names in groups.items()]


def norm(v):
    return re.sub(r"\s+", " ", str(v).strip().lower())


def arg_ok(gold: dict, got: dict) -> bool:
    for k, v in gold.items():
        if k not in got:
            return False
        if k in ("query", "requirement"):
            if norm(v) not in norm(got[k]):
                return False
        elif isinstance(v, bool):
            if bool(got[k]) is not v and norm(got[k]) != norm(v):
                return False
        elif isinstance(v, (int, float)):
            try:
                if abs(float(got[k]) - float(v)) > 1e-6:
                    return False
            except (TypeError, ValueError):
                return False
        elif norm(got[k]) != norm(v):
            return False
    return True


async def run_design(design: str, tools: list[dict], node: str) -> list[dict]:
    from agent import llm
    from agent.prompts import load_prompt

    model = llm.chat_model(node, temperature=0).bind_tools(tools, tool_choice="auto")
    sem = asyncio.Semaphore(3)

    async def one(i: int, task: str, gold_tool: str, gold_args: dict) -> dict:
        async with sem:
            for attempt in range(3):
                try:
                    msg = await model.ainvoke([{"role": "system", "content": load_prompt("tool_task_agent")},
                                               {"role": "user", "content": task}])
                    break
                except Exception as exc:  # noqa: BLE001
                    err = str(exc)[:200]
                    await asyncio.sleep(5 * (attempt + 1))
            else:
                return {"design": design, "task": i, "error": err, "tool_ok": False, "args_ok": False, "tokens": 0}
        calls = msg.tool_calls or []
        meta = getattr(msg, "usage_metadata", None) or {}
        first = calls[0] if calls else {"name": None, "args": {}}
        name, args = first["name"], first.get("args") or {}
        if design == "coarse" and name:
            name, args = args.get("action"), args.get("params") or {}
        tool_ok = name == gold_tool
        return {"design": design, "task": i, "gold_tool": gold_tool, "called": name, "n_calls": len(calls),
                "tool_ok": tool_ok, "args_ok": tool_ok and arg_ok(gold_args, args), "args": args,
                "tokens": meta.get("input_tokens", 0) + meta.get("output_tokens", 0), "error": None}

    return await asyncio.gather(*(one(i, t, g, a) for i, (t, g, a) in enumerate(TASKS)))


async def main_async(args) -> dict:
    designs = {"fine": await fine_tools(False), "coarse": await coarse_tools(), "best": await fine_tools(True)}
    rows, summary = [], {}
    for name, tools in designs.items():
        res = await run_design(name, tools, args.node)
        rows += res
        summary[name] = {"tools": len(tools), "tasks": len(res),
                         "tool_selection_accuracy": round(sum(r["tool_ok"] for r in res) / len(res), 4),
                         "argument_accuracy": round(sum(r["args_ok"] for r in res) / len(res), 4),
                         "tokens_per_task": mean(r["tokens"] for r in res),
                         "schema_chars": len(json.dumps(tools)), "errors": sum(1 for r in res if r["error"])}
        print(name, summary[name], flush=True)
    return {"summary": summary, "rows": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="open_qwen")
    ap.add_argument("--node", default="intent", help="node whose model (small tier) runs the tasks")
    args = ap.parse_args(argv)
    H.setup_env(cache=False, profile=args.profile)
    from agent import llm, settings

    out = H.run(main_async(args))
    model = llm.spec_for(args.node).model
    H.write_result(f"tool_granularity_{args.profile}.json", {"profile": settings.config()["profile"], "model": model,
                                                             "summary": out["summary"], "n_tasks": len(TASKS)})
    H.write_result(f"tool_granularity_{args.profile}_per_task.jsonl", out["rows"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
