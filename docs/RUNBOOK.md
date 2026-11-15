# Runbook

How to run GigBid, how it is scheduled, and how to do the failure drills for the viva. Architecture is in `docs/ARCHITECTURE.md`, tools in `docs/TOOLS.md`.

## Run locally without Docker

You need `uv`, Node 22 and a Postgres with the `vector` extension. The simplest Postgres is the embedded one (`pgserver`, a dev dependency). `evals/runners/harness.py` uses the same call.

```bash
uv sync
(cd apps/web && npm ci)

# 1. Start the embedded Postgres and print its URI. Data lives in .pgdata (git-ignored).
uv run python -c "import pgserver; print(pgserver.get_server('.pgdata', cleanup_mode=None).get_uri())"

# 2. Environment. Copy .env.example to .env and fill it, or export directly.
export DATABASE_URL=<the URI from step 1>
export GIGSIM_DATABASE_URL=$DATABASE_URL
export APP_SECRET=$(uv run python -c "import secrets; print(secrets.token_urlsafe(48))")
export TOKEN_ENC_KEY=$(uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export GROQ_API_KEY=<your key>          # profile "open"
export REVIEWER_EMAIL=reviewer@example.com
export REVIEWER_PASSWORD=<choose one>   # seeds a login on first start

# 3. API with GigSim and the three MCP servers mounted in process, plus the web dev server
make dev
```

`make dev` runs `INPROC_SERVICES=1 MCP_TRANSPORT=inproc GIGSIM_BASE_URL=inproc uvicorn apps.api.main:app --port 8000` and `npm run dev` in `apps/web`. The web app is on `http://localhost:5173` and proxies `/api` to port 8000.

In this mode there is no Redis and no Arq worker. A queued run is executed by the SSE stream request that watches it (the run panel in the web app opens it), or by the tick endpoint (see Scheduling).

`agent/settings.py` reads a `.env` file in the repository root at import time. It sets only non-empty values and never overrides a variable that is already set in the shell. `.env` is git-ignored. Do not commit it.

Other useful commands (from the `Makefile`):

| Command | What it does |
|---|---|
| `make test` | Unit, contract, MCP and GigSim tests, then the web e2e tests |
| `make lint` | Error-only ruff check, prompt location check, GigSim checksum check, README numbers check |
| `make data` | Regenerates the synthetic data (`scripts/generate_data.py`, seed 4016) |
| `make smoke` | 10-job smoke eval with the thresholds in `evals/thresholds.yaml` |
| `make api`, `make worker`, `make gigsim`, `make mcp` | Run one service each, for the multi-process setup |

The evals do not need `make dev`. `evals/runners/harness.py` starts the embedded Postgres itself, mounts GigSim and the MCP servers in process, and uses an in-memory checkpointer. It caches model answers on disk when `GIGBID_LLM_CACHE=1`.

Note: the Makefile targets `seed` and `demo` and the last step of `make eval` point to files that are not in the repository at the time of writing (`scripts/seed_demo.py`, `scripts/demo_one_job.py`, `evals/runners/make_tables.py`).

## Run with docker compose

```bash
export APP_SECRET=...      # required, compose refuses to start without it
export TOKEN_ENC_KEY=...   # required
docker compose -f infra/docker-compose.yml up --build
```

Compose reads `.env` in the working directory for these variables. Ports: web 3000, API 8000, GigSim 8081. The MCP servers (8101, 8102, 8103), Postgres and Redis stay on the compose network. The worker is the Arq worker. To run models locally through Ollama, start the `local-models` profile and set `GIGBID_PROFILE=local`.

## Environment variables

`.env.example` in the repository root lists all of them. Secrets there are empty.

| Variable | Used by | Meaning |
|---|---|---|
| `DATABASE_URL` | agent, API, MCP servers, worker | Main Postgres URI. Checkpointer, store, runs, audit log |
| `GIGSIM_DATABASE_URL` | GigSim | Postgres URI for GigSim's own tables (schema `gigsim`). Can be the same database |
| `REDIS_URL` | API, worker | Set: runs go through Arq. Not set: inline mode (serverless) |
| `APP_SECRET` | API, MCP servers | Signs web sessions and MCP service tokens (HS256). Required |
| `TOKEN_ENC_KEY` | API, marketplace server | Fernet key that encrypts marketplace and OAuth tokens at rest |
| `GROQ_API_KEY` | agent | Open profile models on Groq |
| `OPENAI_API_KEY` | agent, GigSim | Paid profile. Also GigSim's `llm` client mode when no GigSim key is set |
| `OLLAMA_BASE_URL`, `OLLAMA_API_KEY` | agent | Local profile through Ollama |
| `LANGSMITH_API_KEY` | agent | Enables LangSmith tracing. Without it tracing is switched off |
| `LANGSMITH_PROJECT` | agent | LangSmith project name (default `gigbid`) |
| `GIGBID_PROFILE` | agent | Model profile: `open`, `open_qwen`, `local`, `paid`. Overrides `profile:` in the config |
| `MARKETPLACE_MODE` | agent, marketplace server | `gigsim` or `upwork_live`. Overrides `marketplace.mode` |
| `MCP_TRANSPORT` | agent | `http` or `inproc`. Overrides `mcp.transport` |
| `MCP_PORTFOLIO_URL`, `MCP_MARKETPLACE_URL`, `MCP_WORKSPACE_URL` | agent | Server URLs for the `http` transport |
| `GIGSIM_BASE_URL` | marketplace adapter | GigSim URL, or `inproc` to call it inside the same process |
| `INPROC_SERVICES` | API | `1` mounts GigSim and the MCP servers in the API process |
| `REVIEWER_EMAIL`, `REVIEWER_PASSWORD`, `REVIEWER_PERSONA` | API | Seeds a login with a saved search on first start (persona default `ai_ml`) |
| `CRON_SECRET` | API | Bearer secret for `/api/worker/tick` |
| `TICK_BUDGET_S` | API | Time budget of one tick (default 200) |
| `PUBLIC_BASE_URL` | API | Public origin, used for the Upwork OAuth client metadata and redirect URI |
| `CORS_ORIGINS`, `WEB_DIST` | API | CORS list (default `*`) and the folder of the built web app |
| `POLICY_VERSION` | agent | Overrides `policy.version` |
| `RAG_VARIANT` | agent | Overrides `rag.variant` |
| `GIGBID_CONFIG` | agent | Path of another config file |
| `GIGBID_DEFENCES` | agent | `off` disables the injection defences (for the injection study only) |
| `GIGBID_LLM_CACHE` | agent | `1` caches model calls on disk (evals) |
| `GIGBID_LEDGER_PG` | agent | `1` records billed spend in Postgres (the deployment sets it) |
| `GIGBID_EXTERNAL_SPEND_USD` | agent | Spend made elsewhere, added to the cap check |
| `GIGBID_MODEL_DIR`, `HF_HOME` | rag | Where embedding and reranker models are cached |
| `PORTFOLIO_OWNER`, `PORTFOLIO_REQUIRE_AUTH` | portfolio server | Persona folder to serve, and whether a token is required |
| `GIGSIM_ADMIN_TOKEN` | GigSim | Admin bearer token (default `gigsim-admin-dev`) |
| `GIGSIM_RATE_LIMIT_PER_MIN` | GigSim | Requests per minute per token (default 60, 0 disables) |
| `GIGSIM_ERROR_RATE` | GigSim | Chance of a 503 on non-admin requests (default 0.02) |
| `GIGSIM_TIME_SCALE` | GigSim | Simulated seconds per real second (default 60, 0 freezes time) |
| `GIGSIM_POLICY_VERSION` | GigSim | Active platform policy, `1` or `2` |
| `GIGSIM_CLIENT_MODE` | GigSim | `llm` or `heuristic` (default `llm` if a key is set) |
| `GIGSIM_LLM_MODEL`, `GIGSIM_LLM_BASE_URL`, `GIGSIM_LLM_API_KEY` | GigSim | Model settings for `llm` client mode |
| `GIGSIM_SEED_DIR`, `GIGSIM_DATA_DIR` | GigSim | Seed and data folders |
| `GIGSIM_ERROR_SEED` | GigSim | Seed of the error-injection random numbers (default 4016) |
| `GIGSIM_STREAM_INTERVAL_HOURS` | GigSim | Release spacing for stream jobs without an offset (default 0.25) |

The full GigSim table, with defaults, is in `gigsim/README.md`.

## Scheduling

Saved searches (table `saved_searches`) have an `interval_minutes` (default 30). `worker/tasks.py` `scout_user()` raises it to a floor that depends on the mode:

- `scheduling.gigsim_scout_interval_minutes`: 30 for GigSim.
- `scheduling.live_scout_interval_minutes`: 240 for live Upwork.

Why 240 minutes in live mode:

- Upwork treats aggressive polling as scraping. We want to stay well inside approved use.
- 240 minutes is at most 6 polls a day per search. That is a small number of requests.
- Jobs stay open for days, so a poll every four hours loses nothing a freelancer could act on.

How it runs:

- docker compose: the Arq worker runs `scout_all` every 10 minutes. Each search still waits for its own interval. `sweep` runs every 2 minutes to recover parked runs and drain anything queued.
- Vercel: there is no long-running worker. A GitHub Actions workflow (`.github/workflows/tick.yml`, cron `17 */3 * * *`) calls `POST /api/worker/tick` every 3 hours with `Authorization: Bearer $CRON_SECRET`. Repository secrets: `CRON_SECRET`, `PUBLIC_BASE_URL`. A tick scouts due searches (at most 3 new jobs per user), polls marketplace events, recovers parked runs and executes up to 4 queued runs.
- Because a check happens only every 3 hours on Vercel, a search with a 240-minute floor actually runs every 6 hours (the first tick after 180 minutes is too early, the second is not).
- Run a tick by hand: `curl -X POST -H "Authorization: Bearer $CRON_SECRET" $PUBLIC_BASE_URL/api/worker/tick`.
- The "Scout now" button calls `POST /api/scout`, which forces the searches and ignores the interval.

## Idempotency and double execution

Three layers keep a run, a draft and a submit from happening twice:

1. Run claim. `runner.claim()` is one `UPDATE` with `FOR UPDATE SKIP LOCKED`. A duplicate Arq message or a second worker gets nothing. The run id is also used as the Arq job id.
2. Heartbeat. A running run refreshes `heartbeat_at` every 15 s while events arrive. A run whose heartbeat is older than 180 s is treated as dead and can be claimed again. It continues from the last checkpoint.
3. Idempotency keys on every write tool. Keys are built from stable values (job, user, content hash, draft id), so a retried node sends the same key. The marketplace server and GigSim both store the key with the request hash. Same key and same request: stored answer, no second action. Same key and different request: refused.

The approval decision itself is guarded too. `POST /api/approvals/{thread_id}/decision` flips `pending` to `approved`, `edited` or `rejected` in one `UPDATE ... WHERE status='pending'`. A double click gets HTTP 409.

## Viva drills

### Drill 1: kill the marketplace server

Docker compose: `docker compose -f infra/docker-compose.yml stop mcp-marketplace`.
Local multi-process (`make mcp`): stop the process on port 8102.
`make dev` (everything in one process): GigSim cannot be stopped on its own, so make it fail instead. This follows the same path from the adapter upward.

```bash
curl -X POST -H "Authorization: Bearer gigsim-admin-dev" -H "content-type: application/json" \
     -d '{"error_rate": 1}' http://localhost:8000/gigsim/v1/admin/config
# undo with {"error_rate": 0}
```

What the user sees:

- Within about 10 s the UI shows a banner: "Marketplace unavailable - GigBid has queued your work and will resume automatically." The banner reads `/api/health` (`marketplace: "down"`, cached for 10 s).
- The run in progress shows status `waiting_marketplace`.

Where it is handled:

- `mcp_servers/marketplace/adapters/gigsim.py` retries with backoff, then raises `MarketplaceUnavailable`. The server turns it into `MARKETPLACE_UNAVAILABLE`.
- `agent/mcp_client.py`: `McpGateway.call()` raises `MarketplaceDown` (also when the server is unreachable after the retries).
- `agent/nodes/_base.py` re-raises it, so the checkpoint keeps the node pending. The graph's `RetryPolicy` does not retry it (`_retryable` in `agent/graphs/bid_graph.py`).
- `agent/runner.py` `execute()` sets the run to `waiting_marketplace` and writes a `marketplace_down` event.
- `worker/tasks.py` `recover()` probes the marketplace with `get_connects_balance`. When it answers, parked runs go back to `queued` and continue from their checkpoint. With the Arq worker this happens within 2 minutes (the `sweep` cron). On Vercel it happens at the next tick, or call the tick by hand.

Bring the marketplace back and watch the banner disappear and the run finish.

### Drill 2: crash the worker before submit

1. Open a proposal at the approval gate. Approve it.
2. Kill the worker straight away: `docker compose -f infra/docker-compose.yml kill worker`, then start it again.

Why the Connects are spent at most once:

- The approval decision was stored before the resume run was queued. The `approvals` row is already decided and the graph checkpoint holds the paused state.
- The resume run stays `running` with a stale heartbeat. After 180 s `claim()` takes it again. `execute()` either resumes the interrupt again (if the checkpoint was not yet advanced) or continues from the checkpoint at `submit`.
- `submit` (`agent/nodes/approval.py`) uses deterministic keys: `gb-` plus a hash of `job:user`, the word `draft` and a hash of the cover letter, then the same with the draft id for the submit. A second execution sends the same keys.
- `create_proposal_draft` and `submit_proposal` check the key in `mcp_idempotency` and return the stored result. If the crash came after GigSim processed the call but before our table was written, GigSim itself returns the stored answer (`Idempotent-Replay: true`). GigSim also refuses a second submitted proposal for the same job (`409 already_submitted`).
- Check it: `select tool, args->>'idempotency_key', ok from audit_log order by id desc limit 10;` and `GET /v1/me/connects` on GigSim. The Connects were charged once.

### Drill 3: replay from a checkpoint

```bash
curl -H "Authorization: Bearer $TOKEN" $BASE/api/runs/$RUN_ID/history
# [{"checkpoint_id": "...", "next": ["writer"], "created_at": "...", "status": "..."}, ...]
curl -X POST -H "Authorization: Bearer $TOKEN" $BASE/api/runs/$RUN_ID/replay/$CHECKPOINT_ID
```

- `history` lists up to 60 checkpoints of the thread, newest first, with the node that runs next.
- `replay` queues a run of kind `replay` with that `checkpoint_id`. LangGraph forks the thread at the checkpoint, so the original history is untouched. The replay is a new branch.
- Nodes after the checkpoint run again with real model calls, so it costs tokens. A replay from before the approval gate stops at the approval gate again and asks for a new decision. It cannot submit without approval.
- Conversation threads use `conversation_replay` the same way.

### Drill 4: switch GigSim to live mode

Set `marketplace.mode: upwork_live` in `agent/config.yaml`, or `MARKETPLACE_MODE=upwork_live`, and restart the API and the marketplace server.

What changes:

- The Marketplace server uses `adapters/upwork_live.py`. It calls the official Upwork MCP server with the user's OAuth token. Each user must connect Upwork first (`GET /api/oauth/upwork/start`, redirect back to `/api/oauth/upwork/callback`). `PUBLIC_BASE_URL` must be a public https origin because Upwork fetches the client metadata document from it. Without a connected account tools fail with `NOT_CONNECTED`.
- The scouting floor becomes 240 minutes.
- `submit_proposal` does not submit. It leaves the draft for the user to confirm on Upwork.
- `get_pricing_stats` still uses GigSim's historical statistics. `get_events` returns nothing, so the pipeline does not move by itself and no conversation run starts from events.
- The tool-name map in `adapters/upwork_tools.yaml` is unverified. Expect to fix names after the first real call.

What does not change: both graphs and all nodes, prompts, the MCP tool names and schemas, the approval gate, idempotency keys, the audit log, budgets, and the policy pack check in Compliance.

### Drill 5: the policy change request (policy 1 to 2)

Policy v2 (effective 2026-11-02, `data/policy_pack/policy_v2.yaml`) adds a 50 percent Connects surcharge for jobs with 15 or more proposals, and allows only `github.com` links in proposals.

1. GigSim side: `GIGSIM_POLICY_VERSION=2` at start, or live with `POST /v1/admin/config {"policy_version": "2"}` (admin token, the value is a string). The admin setting is stored in the database and overrides the environment.
2. GigBid side: set `policy.version: 2` in `agent/config.yaml`, or `POLICY_VERSION=2`, then restart the API (the policy pack is cached per process).
3. Check `/api/health`: it reports `policy_version`.

What follows without code changes:

- Pricing reads the Connects cost from `quote_connects`, so the surcharge shows up in the expected-value check.
- The Compliance Guard loads `policy_v2.yaml`. The `link_restriction` rule makes the deterministic scrub remove any URL that is not on github.com.
- If you change only GigSim, GigSim answers `422 policy_violation` when a draft has a bad link. That arrives as `MARKETPLACE_REJECTED` and is not retried. Change both sides together.

## Troubleshooting

| Symptom | Check |
|---|---|
| `APP_SECRET is not set` | Export it or put it in `.env`. MCP service tokens and web sessions need it |
| `DATABASE_URL is not set` | Start Postgres and export the URI |
| `TOKEN_ENC_KEY is not set` | Needs a Fernet key, see the command above |
| Run stays `queued` in `make dev` | Open the run in the UI so the SSE stream starts it, or call `/api/worker/tick` with `CRON_SECRET` set |
| Run stays `running` after a crash | Wait 180 s for the stale heartbeat, then it is claimed again |
| Run is `dead_letter` | Three attempts failed. See `runs.error` and the `error` events in `run_events` |
| Run says `Spend cap reached` | Only the `paid` profile is capped. See `llm.billed_cap_usd` and the `llm_ledger` table |
