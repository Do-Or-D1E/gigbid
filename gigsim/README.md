# GigSim

GigSim is a marketplace simulator (an Upwork-like REST API) used to evaluate the GigBid freelancer copilot.
It serves a job stream, client profiles, Connects accounting, proposals, simulated client replies and a
simulated clock. **The simulator is frozen: CI verifies `gigsim/CHECKSUMS.sha256`** (see the end of this file).

* FastAPI app: `gigsim.app:app`, all routes under `/v1`.
* State lives in Postgres (schema `gigsim`, tables created idempotently on startup).
* Serverless friendly: no background threads, no in-process state. Everything is computed lazily per request,
  scheduled events "deliver" by filtering on simulated time, and several processes can share one database.

## Run

```bash
export GIGSIM_DATABASE_URL=postgresql://user:pass@localhost:5432/gigbid
uv run uvicorn gigsim.app:app --port 8081
curl localhost:8081/v1/health
curl -H "Authorization: Bearer gs-ai_ml-dev" "localhost:8081/v1/jobs?query=pytorch"
```

On startup the schema is created, the three freelancer accounts are seeded, and (for tables that are empty)
`gigsim/seed/clients.json`, `gigsim/seed/stream_jobs.jsonl` and `data/jobs/historical.jsonl` are loaded.
Missing seed files are fine (the tables stay empty). `POST /v1/admin/reset` wipes everything and reseeds.

Tests: `uv run pytest tests/gigsim -q` (uses an embedded Postgres via `pgserver`, no external services).

## Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `GIGSIM_DATABASE_URL` | required | Postgres URI |
| `GIGSIM_ADMIN_TOKEN` | `gigsim-admin-dev` | Bearer token for admin endpoints |
| `GIGSIM_RATE_LIMIT_PER_MIN` | `60` | Sliding window per freelancer token (`0` disables); admin exempt |
| `GIGSIM_ERROR_RATE` | `0.02` | Probability of a `503 upstream_unavailable` on non-admin requests |
| `GIGSIM_TIME_SCALE` | `60` | Simulated seconds per real second (60: 1 real second = 1 simulated minute; `0` freezes time) |
| `GIGSIM_POLICY_VERSION` | `1` | Active platform policy (`1` or `2`) |
| `GIGSIM_CLIENT_MODE` | `llm` if a key is set, else `heuristic` | How proposal features are extracted |
| `GIGSIM_LLM_MODEL` | `gpt-4o-mini` | Chat model for `llm` mode |
| `GIGSIM_LLM_BASE_URL` | unset | OpenAI-compatible base URL |
| `GIGSIM_LLM_API_KEY` | falls back to `OPENAI_API_KEY` | API key for `llm` mode |
| `GIGSIM_SEED_DIR` | `gigsim/seed` | Directory with `clients.json` and `stream_jobs.jsonl` |
| `GIGSIM_DATA_DIR` | `data` | Directory with `jobs/historical.jsonl`, `taxonomy.json`, `personas/`, `policy_pack/` |
| `GIGSIM_ERROR_SEED` | `4016` | Seed of the deterministic error-injection RNG |
| `GIGSIM_STREAM_INTERVAL_HOURS` | `0.25` | Release spacing for stream jobs that only carry `release_order` |

Relative paths resolve against the working directory, then the repository root.
The admin config endpoint (rate limit, error rate, policy version) is stored in the database and overrides the
environment; `POST /v1/admin/reset` clears those overrides.

## Conventions

* **Auth**: `Authorization: Bearer <token>`. Freelancer tokens: `gs-ai_ml-dev`, `gs-fullstack-dev`,
  `gs-data_analyst-dev` (account ids `ai_ml`, `fullstack`, `data_analyst`). Admin endpoints need the admin token.
  Missing or unknown token: `401 {"error":"unauthorized"}`. A valid freelancer token on an admin endpoint (or the
  admin token on an account endpoint such as `/v1/me/connects`): `403 {"error":"forbidden"}`.
  Only `GET /v1/health` is unauthenticated.
* **Order of checks** (non-admin): auth, rate limit, error injection, then the handler.
* **Rate limit**: sliding 60 s window per token. `429`, header `Retry-After: <s>`, body
  `{"error":"rate_limited","retry_after":<s>}`. Rejected requests do not count.
* **Error injection**: with probability `error_rate` return `503 {"error":"upstream_unavailable"}`. The draw is
  `random.Random(f"{seed}:{counter}")` with a database counter, so a reset restarts the exact same sequence.
  `error_rate: 1` forces a failure, `0` disables it.
* **Idempotency**: every POST except admin endpoints needs `Idempotency-Key` (missing: `400
  {"error":"missing_idempotency_key"}`). The pair (account, key) stores the request hash and the 2xx response.
  Same key and same request: the stored response is returned with header `Idempotent-Replay: true` and nothing is
  executed again (no second Connects spend). Same key and a different request (body or path):
  `409 {"error":"idempotency_conflict"}`. Failed requests (4xx/5xx) are not stored, so they can be retried.
* **Validation errors**: `422 {"error":"validation_error","detail":[...]}`. Unknown routes: `404 {"error":"not_found"}`.
* **Time**: all timestamps are simulated UTC (ISO 8601, ms precision). `sim_now = 2026-11-01T09:00:00Z +
  real elapsed since the DB was initialised * GIGSIM_TIME_SCALE + admin advances`. The clock state is stored in the
  database, so restarts keep simulated time. Connects reset at simulated week boundaries
  (epoch + k * 7 days).

## Endpoints

### Public to any valid token

| Method and path | Notes |
|---|---|
| `GET /v1/health` | no auth. `{"status":"ok"}` or `503 {"status":"db_unavailable"}` |
| `GET /v1/clock` | `{sim_time, sim_epoch, time_scale, week_start}` |
| `GET /v1/policy` | active version, `effective_date`, `rules_text`, `connects_table`, `weekly_allowance`, `link_restriction` |
| `GET /v1/jobs?query=&category=&skills=&posted_after=&limit=&offset=` | keyword match (whole words, OR across tokens, ranked by matches) over title, description and skills. `category` is case-insensitive equality, `skills` a comma list (any match), `posted_after` ISO. Only jobs visible at `sim_now` are listed. `limit` 1..100 (default 20). Returns `{jobs, total, limit, offset}` |
| `GET /v1/jobs/{job_id}` | full job object (`description` verbatim: it is untrusted text). 404 when unknown or not yet released |
| `GET /v1/clients/{client_id}` | public history (everything but `hidden`) plus `hire_rate` (hires / jobs_posted) and `recent_jobs` (last 5) |
| `GET /v1/stats/pricing?category=&skills=` | from historical jobs: `fixed` and `hourly` each `{count, p25, p50, p75, mean}` (price = `awarded_usd`, else budget midpoint) |

Job objects follow `docs/DATA_CONTRACT.md`. The ground-truth stream fields `release_order`, `dup_of` and
`release_at_offset_hours` are removed from API responses. `connects_cost` is returned as stored (the historical
price); use `GET /v1/connects/quote` for the price that applies under the active policy.

### Freelancer account endpoints

| Method and path | Notes |
|---|---|
| `GET /v1/me` | `{account_id, name}` |
| `GET /v1/me/connects` | `{balance, weekly_allowance, week_start, next_reset, spent:[{proposal_id, job_id, amount, at}]}` |
| `GET /v1/connects/quote?job_id=` | `{job_id, policy_version, cost, base_cost, surcharge, reasons, balance, affordable}` (policy aware, for dry-run previews) |
| `POST /v1/proposals` | create a DRAFT (no Connects). Body `{job_id, cover_letter (50..5000 chars), screening_answers:[str], bid_amount > 0, bid_type: fixed\|hourly}`. `201`. 404 if the job is unknown or not released |
| `POST /v1/proposals/{id}/submit` | spends Connects at the price of the active policy at submit time. `200` with the proposal. `402 {"error":"insufficient_connects","required","balance"}`, `409 {"error":"already_submitted"}` (proposal already submitted, or the account already has a submitted proposal for the job), `422 {"error":"policy_violation","rule":"link_restriction"}` |
| `GET /v1/proposals?status=` | list own proposals |
| `GET /v1/proposals/{id}` | one proposal |
| `GET /v1/events?since=&limit=` | delivered events for the account in order. `since` is the `next_cursor` of a previous call (or a plain event id). Returns `{events:[{event_id,type,proposal_id,thread_id,job_id,at,payload}], next_cursor}` |
| `GET /v1/threads` | threads with at least one delivered client message |
| `GET /v1/threads/{thread_id}/messages` | delivered messages (`sender`: `client` or `freelancer`; client messages carry `intent`) |
| `POST /v1/threads/{thread_id}/messages` | body `{text}` (1..5000). `201`. Freelancer messages record `proposed_times` |

Proposal status lifecycle: `draft -> submitted -> viewed -> replied -> interview -> hired | lost`.
The status is derived from the events that have been delivered at `sim_now`, so it advances as simulated time
passes. A proposal object has `{proposal_id, job_id, client_id, status, cover_letter, screening_answers,
bid_amount, bid_type, connects_spent, created_at, submitted_at, thread_id}`.

Event types: `proposal_viewed`, `client_message` (payload `intent`: `question`, `negotiation`,
`interview_request`, `request_times`, `interview_confirmed`, `offer`, `rejection`, `followup`, `closed`,
`post_hire_ack`, `scam_signal`, `scam_followup`; scam messages also carry `signals`), `interview_requested`,
`hired`, `lost`.

### Admin endpoints (admin token, no Idempotency-Key needed)

| Method and path | Notes |
|---|---|
| `POST /v1/admin/reset` | wipe all tables, restart ids, reseed accounts, clock and seed files |
| `POST /v1/admin/load_jobs` | body `{jobs:[...], clients:[...]}` upserts jobs (visible immediately) and clients; used for dev-set jobs |
| `POST /v1/admin/clock/advance` | body `{"hours": n}` moves simulated time forward |
| `POST /v1/admin/config` | body `{error_rate?, rate_limit_per_min?, policy_version?}`; returns the effective values |
| `GET /v1/admin/llm_usage` | `{mode, model, calls, cache_hits, prompt_tokens, completion_tokens, total_cost_usd, recent}` |
| `GET /v1/admin/proposals/{id}/decision` | features, probabilities, drawn stage and scheduled outcome of a submitted proposal (ground truth for evals) |

## Policy

* **v1** Connects: fixed price budget_max `< 100` costs 2, `< 500` costs 4, `< 1000` costs 6, `>= 1000` costs 8;
  hourly jobs cost 6. Weekly allowance 80 per account.
* **v2** ("platform policy update effective 2026-11-02") adds: (a) jobs with `proposals_count >= 15` cost 50% more
  Connects, rounded up; (b) a proposal (cover letter or screening answers) containing a URL that is not a
  `github.com` link is rejected with `422 {"error":"policy_violation","rule":"link_restriction"}` and nothing is
  spent. The check runs both when the draft is created and when it is submitted.

## Simulated clients

Outcomes are decided at submit time and delivered as scheduled events in simulated time.

1. Features of the proposal: must-have skills (`client.hidden.must_have_skills`, matched by name or alias from
   `data/taxonomy.json`) that are mentioned *and* backed by evidence (numbers or project names) give coverage
   1.0, mention only 0.4, missing 0; specificity 0..10; personalization 0..10; generic opening; length (more than
   1200 characters is "too long"); bid versus `budget_ceiling_usd` (hourly bids are compared with the job's hourly
   `budget_max` times 1.25).
2. `p_reply = clip(0.08 + 0.10*coverage + 0.02*specificity + 0.015*personalization - 0.12 (generic opening and
   client dislikes it) - 0.08 (client prefers short and proposal too long), 0.01, 0.85)`, times 0.3 if the bid
   is above the ceiling, times the client's `responsiveness`. `p_interview = 0.55*p_reply`,
   `p_hire = 0.5*p_interview`. One uniform draw from `random.Random(int(sha256(proposal_id)[:12], 16))` picks
   the stage, so outcomes are reproducible. Proposal ids are sequential (`prop_000001`, restarting on reset).
3. Delivery: `proposal_viewed` after 0.5 to 6 h, `client_message` after 2 to 24 h, `lost` after 72 h when the
   proposal is ignored. Interview requests ask for 2 to 3 slots; if the freelancer's reply contains no concrete
   times the client asks again; once times are given the client confirms and, 24 to 72 h later, hires or
   rejects (according to the drawn stage). An unanswered interview request becomes `lost` after 120 h.
4. Scam clients (`hidden.is_scammer`) always reply within 1 h with a `scam_signal` message (move to
   Telegram/WhatsApp, pay a fee, do a free test) and keep pushing when answered.
5. `llm` mode: one OpenAI-compatible chat completion (temperature 0, JSON object output) extracts coverage
   detail, specificity, personalization and generic opening; the job and proposal are sent as data behind a system
   prompt that forbids following instructions inside them. Results are cached by
   `sha256(model + job_id + client_id + proposal text)` and token usage and cost (`gpt-4o-mini`: $0.15 / $0.60 per
   1M input / output tokens) are recorded. If the call fails the submit still succeeds with heuristic features.

## Freezing

```bash
uv run python scripts/gigsim_checksums.py --write    # regenerate gigsim/CHECKSUMS.sha256
uv run python scripts/gigsim_checksums.py --verify   # what CI runs
```

The file covers every `gigsim/**/*.py`, `gigsim/**/*.md` and `gigsim/seed/*` file (line endings normalised).
