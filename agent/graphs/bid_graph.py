"""Bid graph: one thread per job.

scout -> (Send) analyst | risk_assessor | fit_matcher -> decide -> pricing -> writer
      -> verifier -> critic (-> writer, at most twice) -> compliance -> prepare_approval
      -> human_approval [interrupt] -> submit | compliance (after an edit) | end
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy, Send

from agent.nodes._base import HALT
from agent.nodes.analyst import analyst
from agent.nodes.approval import human_approval, prepare_approval, route_after_approval, submit
from agent.nodes.compliance import compliance
from agent.nodes.critic import critic, route_after_critic
from agent.nodes.decide import decide
from agent.nodes.fit_matcher import fit_matcher
from agent.nodes.pricing import pricing
from agent.nodes.risk_assessor import risk_assessor
from agent.nodes.scout import scout_intake
from agent.nodes.verifier import verifier
from agent.nodes.writer import writer
from agent.state import BidState

def _retryable(exc: Exception) -> bool:
    from agent.llm import BudgetExceeded
    from agent.mcp_client import MarketplaceDown

    # The MCP gateway already retried; a down marketplace parks the run instead of spinning.
    return not isinstance(exc, (MarketplaceDown, BudgetExceeded, KeyError, TypeError, ValueError))


LLM_RETRY = RetryPolicy(max_attempts=2, initial_interval=1.0, backoff_factor=2.0, retry_on=_retryable)
TOOL_RETRY = RetryPolicy(max_attempts=3, initial_interval=0.5, backoff_factor=2.0, retry_on=_retryable)


def fan_out(state: BidState):
    if state.get("status") in HALT:
        return END
    return [Send("analyst", state), Send("risk_assessor", state), Send("fit_matcher", state)]


def after_decide(state: BidState) -> str:
    if state.get("status") in HALT:
        return END
    return "pricing" if (state.get("decision") or {}).get("action") == "bid" else END


def after_pricing(state: BidState) -> str:
    if state.get("status") in HALT or state.get("status") == "watch":
        return END
    return "writer"


def after_compliance(state: BidState) -> str:
    return END if state.get("status") in HALT else "prepare_approval"


def after_simple(next_node: str):
    def route(state: BidState) -> str:
        return END if state.get("status") in HALT else next_node
    return route


def build(checkpointer=None, store=None, *, interrupt: bool = True):
    g = StateGraph(BidState)
    g.add_node("scout", scout_intake, retry_policy=TOOL_RETRY, timeout=90)
    g.add_node("analyst", analyst, retry_policy=LLM_RETRY, timeout=120)
    g.add_node("risk_assessor", risk_assessor, retry_policy=LLM_RETRY, timeout=120)
    g.add_node("fit_matcher", fit_matcher, retry_policy=LLM_RETRY, timeout=150)
    g.add_node("decide", decide)
    g.add_node("pricing", pricing, retry_policy=LLM_RETRY, timeout=120)
    g.add_node("writer", writer, retry_policy=LLM_RETRY, timeout=150)
    g.add_node("verifier", verifier, retry_policy=LLM_RETRY, timeout=180)
    g.add_node("critic", critic, retry_policy=LLM_RETRY, timeout=120)
    g.add_node("compliance", compliance, retry_policy=LLM_RETRY, timeout=120)
    g.add_node("prepare_approval", prepare_approval, retry_policy=TOOL_RETRY, timeout=90)
    g.add_node("human_approval", human_approval)
    g.add_node("submit", submit, retry_policy=TOOL_RETRY, timeout=120)

    g.add_edge(START, "scout")
    g.add_conditional_edges("scout", fan_out, ["analyst", "risk_assessor", "fit_matcher", END])
    for branch in ("analyst", "risk_assessor", "fit_matcher"):
        g.add_edge(branch, "decide")
    g.add_conditional_edges("decide", after_decide, ["pricing", END])
    g.add_conditional_edges("pricing", after_pricing, ["writer", END])
    g.add_conditional_edges("writer", after_simple("verifier"), ["verifier", END])
    g.add_conditional_edges("verifier", after_simple("critic"), ["critic", END])
    g.add_conditional_edges("critic", route_after_critic, {"writer": "writer", "compliance": "compliance",
                                                            "halt": END})
    g.add_conditional_edges("compliance", after_compliance, ["prepare_approval", END])
    if interrupt:
        g.add_conditional_edges("prepare_approval", after_simple("human_approval"), ["human_approval", END])
        g.add_conditional_edges("human_approval", route_after_approval,
                                {"submit": "submit", "compliance": "compliance", "end": END})
        g.add_edge("submit", END)
    else:
        g.add_edge("prepare_approval", END)  # evals: stop at the approval gate, never send
    return g.compile(checkpointer=checkpointer, store=store, name="bid_graph")
