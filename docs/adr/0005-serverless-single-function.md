# ADR 0005: Deploy as one serverless function on Vercel

Status: accepted

## Context

The assignment needs a public deployment, and we have to stay on free tiers. The full design has many parts: a web app, an API, a worker, three MCP servers, GigSim, Postgres and Redis. Docker compose runs all of that, but the free Vercel tier runs functions, not long-lived containers. Vercel Hobby cron runs only once a day.

## Decision

- One Python function (`api/index.py`, `vercel.json`) serves the API, the built web app, GigSim and the MCP servers. `INPROC_SERVICES=1` mounts GigSim and the MCP servers inside the API process (ADR 0006).
- No Redis and no always-on worker. A run is a row in the `runs` table. The SSE stream request that watches a queued run claims it and executes it (`apps/api/streaming.py`). If that request ends early, the heartbeat goes stale and the next stream request or tick picks the run up from its checkpoint.
- The worker becomes a tick endpoint, `/api/worker/tick`, protected by `CRON_SECRET`. A GitHub Actions workflow calls it every 3 hours (`.github/workflows/tick.yml`). A tick scouts due searches, polls events, recovers parked runs and drains a few queued runs inside a time budget.
- State lives in a hosted Postgres with pgvector. The spend ledger writes to Postgres too (`GIGBID_LEDGER_PG=1`), because function disks are temporary.
- Docker compose stays as the full deployment with Redis and an Arq worker. Both modes share `agent/runner.py`.

## Consequences

- It runs on free tiers with one deploy.
- Cold starts are slower, and a function has a time limit (`maxDuration` 300 s). Long runs must fit in that limit or continue from a checkpoint.
- Background work is coarse. Scheduled scouting happens every 3 hours at best, which also fits the polite polling interval in live mode.
- The in-process mode and the compose mode are two code paths for dispatch. The claim, checkpoint and idempotency design keeps them consistent.
- Functions have no local disk to rely on, so model files are cached under `/tmp` and are downloaded again after a cold start.
