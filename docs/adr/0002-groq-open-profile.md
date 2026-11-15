# ADR 0002: Open-weight models through Groq as the default profile

Status: accepted

## Context

The brief favours open models. We looked at running them ourselves, and that did not work here:

- The development machine has no usable GPU for these models and little free disk, so local models do not fit. Free hosts have no GPU either.
- Hugging Face inference credits were used up.
- We still need a strong model for writing, judging and replies, and a cheap one for frequent steps.

## Decision

- The default profile is `open` in `agent/config.yaml`. It uses open-weight models served by Groq's OpenAI-compatible API: a small tier (`openai/gpt-oss-20b`) for frequent nodes and a strong tier (`openai/gpt-oss-120b`) for writer, critic and liaison. Each tier has a fallback model (`qwen/qwen3.8-27b` for small, `openai/gpt-oss-20b` for strong). A second profile, `open_qwen`, swaps in Qwen for a comparison.
- `local` (Ollama) is defined for people who have a GPU. It is not used for our results.
- `paid` is an optional profile using OpenAI `gpt-4o-mini`. We use it only where it beats the open profile by enough to pay for (see `evals/results/tool_granularity_paid.json`).
- Models are routed per node (`nodes:` in the config), never hard-coded in nodes.
- Spend on billed providers has a hard cap. `agent/llm.py` checks `llm.billed_cap_usd` (2.00 USD) before every billed call. The ledger adds up spend from a local SQLite file, from Postgres (`llm_ledger`) and from `GIGBID_EXTERNAL_SPEND_USD`. Going over the cap raises `BudgetExceeded`, and the node ends in `needs_attention`.
- On errors that look transient, `llm.call()` retries the primary model, then switches to the profile's fallback model.

## Consequences

- No GPU, no model downloads, and a free tier for most work.
- The free tier has rate limits and model names can change. The fallback model covers some of that.
- Groq is marked `billed: false`, so the cap does not apply to it. The cap protects only paid profiles.
- Prompts must work with open models, so structured output uses JSON schema and every result is validated.
- Costs shown for Groq are list-price estimates, kept separate from billed cost.
