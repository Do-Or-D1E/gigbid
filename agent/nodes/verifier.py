"""Claim verification node (B3): runs before the Critic, so the Critic and the human only
see drafts whose unsupported claims were removed or rewritten."""
from __future__ import annotations

from agent.nodes._base import node
from agent.nodes.writer import evidence_for_writer
from rag.verify import verify_and_fix


@node("verifier")
async def verifier(state: dict, config: dict) -> dict:
    draft = dict(state["draft"])
    evidence = evidence_for_writer(state, limit=10)
    text = draft["cover_letter"]
    answers = "\n".join(f"Q: {a['question']}\nA: {a['answer']}" for a in draft.get("screening_answers", []))
    revised, report = await verify_and_fix(text + ("\n\n" + answers if answers else ""), evidence)
    if report.rewritten:
        # Keep screening answers separate: split the revised text back if the model kept the Q/A block.
        cover, _, rest = revised.partition("\nQ: ")
        draft["cover_letter"] = cover.strip()
        if rest and draft.get("screening_answers"):
            qa = ("Q: " + rest).split("\nQ: ")
            new_answers = []
            for block, orig in zip(qa, draft["screening_answers"]):
                _, _, ans = block.partition("\nA: ")
                new_answers.append({"question": orig["question"], "answer": (ans or orig["answer"]).strip()})
            draft["screening_answers"] = new_answers
    prev = state.get("claim_report") or {}
    rep = report.model_dump()
    # The first draft's "before" count is the honest baseline; later rounds keep it.
    if prev:
        rep["unsupported_before_first_draft"] = prev.get("unsupported_before_first_draft", prev.get("unsupported_before"))
    else:
        rep["unsupported_before_first_draft"] = report.unsupported_before
    return {"draft": draft, "claim_report": rep}
