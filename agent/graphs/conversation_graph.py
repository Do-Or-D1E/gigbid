"""Conversation graph: one thread per client conversation.

liaison_read -> intent -> liaison_gather -> liaison (draft) -> message_compliance
             -> message_approval [interrupt] -> send | message_compliance (after edit) | end
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from agent.nodes._base import HALT
from agent.nodes.client_liaison import (classify_intent, draft_reply, gather, liaison_read, message_approval,
                                        message_compliance, route_after_message_approval, send)
from agent.state import ConversationState

from agent.graphs.bid_graph import _retryable  # noqa: E402

RETRY = RetryPolicy(max_attempts=2, initial_interval=1.0, retry_on=_retryable)


def _next(node: str):
    def route(state: ConversationState) -> str:
        return END if state.get("status") in HALT else node
    return route


def build(checkpointer=None, store=None):
    g = StateGraph(ConversationState)
    g.add_node("liaison_read", liaison_read, retry_policy=RETRY, timeout=60)
    g.add_node("intent", classify_intent, retry_policy=RETRY, timeout=90)
    g.add_node("liaison_gather", gather, retry_policy=RETRY, timeout=90)
    g.add_node("liaison", draft_reply, retry_policy=RETRY, timeout=120)
    g.add_node("message_compliance", message_compliance, retry_policy=RETRY, timeout=90)
    g.add_node("message_approval", message_approval)
    g.add_node("send", send, retry_policy=RETRY, timeout=60)
    g.add_edge(START, "liaison_read")
    g.add_conditional_edges("liaison_read", _next("intent"), ["intent", END])
    g.add_conditional_edges("intent", _next("liaison_gather"), ["liaison_gather", END])
    g.add_conditional_edges("liaison_gather", _next("liaison"), ["liaison", END])
    g.add_conditional_edges("liaison", _next("message_compliance"), ["message_compliance", END])
    g.add_conditional_edges("message_compliance", _next("message_approval"), ["message_approval", END])
    g.add_conditional_edges("message_approval", route_after_message_approval,
                            {"send": "send", "message_compliance": "message_compliance", "end": END})
    g.add_edge("send", END)
    return g.compile(checkpointer=checkpointer, store=store, name="conversation_graph")
