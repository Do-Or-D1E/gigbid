# ADR 0007: Plans and commitments are not experience claims

Status: accepted

## Context

After drafting, the claim verifier (`rag/verify.py`) splits the proposal into atomic claims and checks each one against the portfolio evidence. Unsupported claims are removed or rewritten. The critic sends the draft back for another revision if unsupported claims remain, at most twice.

The first version treated every sentence about the freelancer as an experience claim. Sentences such as "I will start with a data audit" or "I can deliver a first version in two weeks" were marked unsupported, because no past project proves a future plan. The rewrite step could not fix them, the critic kept asking for revisions, and the loop never converged to a clean draft.

## Decision

- A claim that is a plan or commitment for this job is not an experience claim. `rag/verify.py` has a `PLAN` pattern for claims that start with phrases such as "I will", "I'll", "I can", "I would", "I plan", "I am available", "my plan" or "our approach". The lexical guard skips those claims.
- Claims about past work still need evidence. A lexical number guard also runs on them: if a claim says "supported" but its numbers (percentages, counts, durations) do not appear in any evidence text, the status drops to `partly_supported`. Models invent numbers more than anything else, so this check works on text and not on a model's opinion.
- A claim with no valid evidence id is `unsupported`, whatever the model said.
- The verifier reports unsupported counts before and after, and keeps the first draft's count as the honest baseline.

## Consequences

- The critic loop ends, and drafts can contain normal plans and offers.
- A sentence that starts with "I will" but also states past work ("I will reuse the pipeline I built that cut cost by 40 percent") can slip past the pattern. The Compliance Guard still sees the claim results and the policy rule on fabricated experience applies, but this is a known gap.
- The number guard is blunt. It matches text, so a correct claim phrased with a different number format may be downgraded.
