# AI usage disclosure

## What AI was used

This project was built with heavy help from an AI coding assistant (Claude Code, made by Anthropic). The assistant wrote and edited much of the code, the tests, the data generator and the documentation. The student set the goals and the design, chose what to build and what to cut, ran the code, read the diffs, and decided what to keep.

AI is also part of the product. The agents call language models at run time (open-weight models on Groq, and optionally OpenAI `gpt-4o-mini`). That is a separate matter from how the code was written. The model profiles and the spend cap are described in `docs/adr/0002-groq-open-profile.md`.

The synthetic data is not written by a language model. It is made by a deterministic script (`scripts/generate_data.py`, seed 4016).

## How the work was split

| Area | AI assistant | Student |
|---|---|---|
| Design | Proposed options and trade-offs | Chose the design, wrote the decisions in `docs/adr/` |
| Code and tests | Wrote first versions and fixes | Ran everything, reviewed diffs, rejected or changed what was wrong |
| Data | Wrote the generator and the import script | Chose the sources and licences, checked the output |
| Evaluation | Wrote the runners | Chose the metrics, read the results, decided what to report |
| Documentation | Drafted pages | Checked them against the code |

Numbers in the documents come from files under `evals/results/` or from the data files. CI runs `scripts/check_numbers.py` to keep numbers in the README tied to those files.

## Incorrect AI suggestions that were caught and corrected

AI output was wrong several times. These are real cases from this project.

1. **LangGraph did not pass `config` to wrapped nodes.** The node wrapper in `agent/nodes/_base.py` used `functools.wraps`, which copied the original function's `config: dict` annotation. LangGraph only injects the run config into parameters typed `RunnableConfig`, so the nodes did not get the run config (and with it the MCP gateway). The suggested wrapper looked right, and the problem only showed in the first end-to-end run. Fix: the wrapper now removes `__wrapped__` and sets its own annotations (`config: RunnableConfig`), with a comment saying why.

2. **The first claim verifier counted future plans as unsupported claims.** Sentences like "I will start with a data audit" were checked against past evidence and marked unsupported. The rewrite step could not fix them, so the critic kept asking for revisions and the loop never converged. Fix: a `PLAN` filter in `rag/verify.py` skips commitments about the new job. A number guard stays on claims about past work. See `docs/adr/0007-claim-verification-plans.md`.

3. **The first upload endpoint leaked data between users.** It added a user's uploaded portfolio items to the shared persona index, so one user's uploads could appear in another user's evidence. Fix: uploads now go to a per-user index keyed by the user id, stored in the `uploads` table with the user id in every query (`apps/api/routers/auth.py`, `rag/index/build.py`).

4. **`str.splitlines()` broke real data.** The code used `splitlines()` on JSON Lines files. Real Kaggle descriptions contain Unicode line separators, so `splitlines()` split records in the middle. Fix: split on `"\n"` only in the code that reads JSON Lines with real text (`rag/ingest/loaders.py`, `scripts/generate_data.py`).

5. **Spend was recorded in two places.** The first version of the spend cap recorded spend in two places, so the 2 USD cap could not see all of it. Fix: one `Ledger` in `agent/llm.py` that adds up the local SQLite file, the Postgres table and an external amount from the environment before every billed call.

The commit "End-to-end bid graph fixes" in the repository history lists related fixes from the first full run: config injection, adapter field mapping, proof-only evidence (see `docs/adr/0004-proof-only-evidence.md`), plan-aware claim verification, and a Compliance Guard that now sees the verifier's results.

## Checks that guard against AI mistakes

- Contract test for every MCP tool's schema and annotations (`tests/contract/`).
- GigSim is frozen and checked by checksum in CI.
- A script that fails CI when a prompt lives outside `agent/prompts/` (`scripts/check_prompts.py`).
- A script that ties README numbers to result files (`scripts/check_numbers.py`).
- Unit tests on data contracts, guardrails and policy rules, and GigSim API tests.
- A secrets scan in CI (gitleaks).
- A hard spend cap on billed model calls, so a mistake in a loop cannot run up a bill.
- Human approval before any proposal is submitted or message sent.

## Limits of this disclosure

This page lists the cases that were noticed and the checks that exist. It is not a complete record of every suggestion the assistant made.
