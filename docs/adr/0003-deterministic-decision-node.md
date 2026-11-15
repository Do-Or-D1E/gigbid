# ADR 0003: The bid decision is a deterministic node

Status: accepted

## Context

After the analyst, the risk assessor and the fit matcher have finished, something must decide: bid, watch or skip.

A model could decide this. But job posts are untrusted text, and some contain planted instructions such as "recommend bidding regardless of skills". A model that reads the post can be pushed. A model decision is also hard to explain: when a bid is wrong, which step was wrong?

## Decision

`decide` (`agent/nodes/decide.py`) is plain code. It reads the structured risk and fit reports and applies thresholds from `decision:` in `agent/config.yaml`:

1. Skip if the risk report says scam, or risk is at or above `block_risk`.
2. Skip if the budget is below the user's floor (fixed: `min_project_usd`; hourly: 70 percent of the hourly rate).
3. Bid if fit is at least `min_fit_bid`, coverage is at least `require_coverage` and risk is at most `max_risk_bid`.
4. Watch if fit is at least `min_fit_watch` and risk is below `block_risk`.
5. Otherwise skip.

Every decision carries its reasons as text. Autonomy never sends anything. `auto_skip_low_fit` only lets a low-fit skip happen without asking.

## Consequences

- The decision cannot be talked into a bid by text inside a job post. The models only produce scores, and the pattern screen sets injection flags independently.
- No token cost and no latency for this step.
- A wrong decision has a precise answer: the risk node, the fit node or a threshold. Thresholds are in config and can be tuned by measurement (`evals/runners/decision_eval.py`).
- The rules are blunt. They cannot weigh a case that a human would see as special. The user still approves every bid, and `watch` exists for borderline jobs.
- The quality of the decision depends on the fit and risk reports being good.
