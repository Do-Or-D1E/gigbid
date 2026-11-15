# ADR 0004: Only proof counts as evidence. Past proposals are bids, not proof

Status: accepted

## Context

The portfolio has case studies, repos, client reviews, a CV, user uploads and past proposals. Past proposals carry an outcome (won, replied, ignored), which is useful.

The first end-to-end run showed a problem. The fit matcher retrieved past proposals as evidence, so claims in the new draft were grounded only in old proposals. A past proposal is what the freelancer once wrote to win a job. It is not proof that the work was done. The Compliance Guard then blocked the draft because the claims were not backed by real experience.

## Decision

- The fit matcher searches only proof types: `rag.proof_types` in the config (`case_study`, `repo`, `review`, `cv`, `upload`). It passes them as a `types` filter to `search_evidence`.
- Only evidence found this way can ground a claim. The writer cites ids from that set, and the claim verifier checks claims against it.
- Past proposals are still indexed and still useful. The retriever uses their outcomes for ranking (`rag.outcome_boost`: won, replied, ignored), and the portfolio MCP server returns them when a caller asks without a type filter.

## Consequences

- Claims in a draft can be traced to something the freelancer actually did.
- Fewer items per requirement, so a requirement can end up with no evidence. The writer then gets it under "no evidence for (do not claim)".
- The retrieval gold labels include some past proposals (won or replied in the same category), so retrieval scores and end-to-end evidence are not the same thing. See `docs/DATA_CARD.md`.
- A freelancer whose portfolio is mostly past proposals will see weaker drafts until they add proof.
