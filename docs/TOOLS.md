# MCP tools

GigBid has three MCP servers of its own and uses two third-party servers. This page lists every tool, its annotations, who may call it and how it is protected.

The tool list and annotations below come from the live server objects (`tool_snapshot()` in `mcp_servers/common.py`) and match `tests/contract/snapshots/*.json`. A contract test (`tests/contract/test_tool_schemas.py`) fails when a tool name, schema or annotation changes without a new snapshot.

Annotation columns use the four MCP hints: `readOnly`, `destructive`, `idempotent`, `openWorld`. `openWorld` is true when the tool talks to something outside the server (the marketplace). It is false for the portfolio and the workspace mock.

## Own servers

| Tool | Server | Read/write | Annotations (readOnly / destructive / idempotent / openWorld) | Auth | Notes |
|---|---|---|---|---|---|
| `search_evidence` | portfolio | read | true / false / true / false | Service token when the server runs over HTTP. None over stdio (local identity) | Finds portfolio items that prove ONE requirement. Optional filters: item types, past-proposal outcome, earliest date, item ids to leave out. Items the user hid in the UI are excluded. Writes an audit row |
| `get_case_study` | portfolio | read | true / false / true / false | Same as above | Loads one item by id (text cut at 12000 characters). Not audited |
| `list_skills` | portfolio | read | true / false / true / false | Same as above | Profile skills and how many items mention each one. Not audited |
| `search_jobs` | marketplace | read | true / false / true / true | Service token | Summaries only. `limit` 1 to 50 |
| `get_job` | marketplace | read | true / false / true / true | Service token | Description is untrusted text |
| `get_client_history` | marketplace | read | true / false / true / true | Service token | Payment verification, spend, hires, ratings |
| `get_connects_balance` | marketplace | read | true / false / true / true | Service token | Balance and weekly allowance |
| `quote_connects` | marketplace | read | true / false / true / true | Service token | Cost under the active platform policy right now |
| `get_pricing_stats` | marketplace | read | true / false / true / true | Service token | Count, p25, p50, p75 of awarded prices for similar jobs |
| `get_policy` | marketplace | read | true / false / true / true | Service token | Active policy. Also used by the `/api/health` probe |
| `list_threads` | marketplace | read | true / false / true / true | Service token | |
| `list_messages` | marketplace | read | true / false / true / true | Service token | Client messages are untrusted text |
| `list_proposals` | marketplace | read | true / false / true / true | Service token | Optional status filter |
| `get_events` | marketplace | read | true / false / true / true | Service token | Cursor based. Used by the worker, not by a graph node |
| `create_proposal_draft` | marketplace | write | false / false / true / true | Service token with `write` scope (not needed for `dry_run`) | No Connects spent. Needs `idempotency_key`. `dry_run=true` returns the exact payload and policy warnings and creates nothing. The draft is created in a separate step from the submit, so a draft can be inspected |
| `submit_proposal` | marketplace | write | false / true / true / true | Service token with `write` scope (not needed for `dry_run`) | Spends Connects, cannot be undone. Needs `idempotency_key`. `dry_run=true` returns Connects cost, balance and balance after. In live mode it returns `awaiting_user_confirmation_on_upwork` and spends nothing |
| `send_message` | marketplace | write | false / true / true / true | Service token with `write` scope (not needed for `dry_run`) | Cannot be undone. Needs `idempotency_key`. `dry_run=true` previews the message and policy warnings. In live mode it calls the Upwork tool that creates a message draft |
| `free_slots` | workspace | read | true / false / true / false | Service token | Weekdays, 09:00 to 17:00 UTC. At most one slot per day. Skips busy blocks and holds |
| `create_interview_hold` | workspace | write | false / false / true / false | Service token | Tentative hold only. Needs `idempotency_key` (8 to 128 characters). A repeat with the same key returns the same hold with `replay=true` |
| `create_email_draft` | workspace | write | false / false / true / false | Service token | Saves a draft, never sends. Needs `idempotency_key`. Drafts are kept in memory in the server process only |

Idempotency details:

- Keys are 8 to 128 characters of `[\w\-:.]`.
- The marketplace server stores `(user, key, request hash, response)` in the table `mcp_idempotency` (in memory when there is no database). The same key with the same request returns the stored response with `replay=true`. The same key with different arguments fails with `IDEMPOTENCY_CONFLICT`.
- GigSim stores `(account, key)` too, so a crash between the marketplace call and our own store still cannot spend twice.
- The graph builds keys from stable values: `agent/nodes/approval.py` hashes the job and user plus a content hash of the cover letter for the draft, and the draft id for the submit.

Resources and prompts of the portfolio server:

| Kind | Name | What it is |
|---|---|---|
| Resource template | `portfolio://case/{item_id}` | Full case study as Markdown |
| Resource template | `portfolio://proposal/{item_id}` | A past proposal with its job summary and outcome |
| Resource template | `portfolio://repo/{item_id}` | Repository README and code files |
| Resource | `portfolio://profile` | Profile JSON: skills, rates, availability |
| Prompt | `answer_screening_question` (argument `question`) | Answer a screening question in 2 to 4 sentences using only evidence, cite item ids |
| Prompt | `check_fit` (argument `job_post`) | List the requirements of a pasted post, report strong, partial or none per requirement, end with a bid-or-skip view |
| Prompt | `pick_case_study` (argument `client_problem`) | Pick the one best case study for a client problem and summarise it in 3 bullets |

## Third-party servers

| Server | URL | How GigBid uses it | Why we trust it |
|---|---|---|---|
| Upwork official MCP | `https://mcp.upwork.com/mcp` | Live mode only (`marketplace.mode: upwork_live`). OAuth 2.1 with PKCE (S256). The client id is a URL that serves a client metadata document (`/api/oauth/upwork/client.json`). The access token is stored encrypted. Writes create drafts only | It is the platform's own server, so using it stays inside the platform's rules. No scraping, no browser automation |
| GitHub official MCP | `https://api.githubcopilot.com/mcp/` | Intended for read-only repo ingestion into the portfolio. It appears in `mcp.servers.github` in `agent/config.yaml`. No code calls it yet: `McpGateway` only connects to portfolio, marketplace and workspace, and `rag/ingest/` has no GitHub loader | It is GitHub's own server. Read-only use limits what a bad tool description can do |

The Upwork tool-name map in `mcp_servers/marketplace/adapters/upwork_tools.yaml` is UNVERIFIED. No Upwork account was available, so the real tool list was never read. The names are guesses from Upwork's public description. The adapter has not been run end to end. The comments in `upwork_tools.yaml` and `upwork_live.py` point to a discovery script, `scripts/upwork_discover.py`, which is not in the repository yet.

Ports not mapped in `upwork_tools.yaml`: `quote_connects` (reads the job), `get_pricing_stats` (falls back to GigSim statistics), `get_policy` (fixed text), `get_events` (empty), `submit_proposal` (never submits).

## Per-agent allowlists

`mcp.allowlists` in `agent/config.yaml`:

| Agent | Allowed tools |
|---|---|
| scout | `search_jobs`, `get_job` |
| risk_assessor | `get_client_history` |
| fit_matcher | `search_evidence`, `list_skills` |
| pricing | `get_pricing_stats`, `get_connects_balance`, `quote_connects` |
| writer | `search_evidence`, `get_case_study` |
| critic | `search_evidence`, `get_case_study` |
| submit | `create_proposal_draft`, `submit_proposal` |
| liaison | `list_threads`, `list_messages`, `send_message`, `free_slots`, `create_interview_hold`, `create_email_draft` |

How the lists are enforced: `McpGateway.tools_for(agent)` filters the tools by this list when tools are handed to a model as LangChain tools. The graph nodes do not use that path. Each node calls its tools directly by name in code (`gw.call("search_jobs", ...)`), so what a node can call is fixed in the node's source. Two differences from the list above:

- The `liaison_gather` node also calls `search_evidence`, which is not in the liaison list.
- The writer and critic nodes call no tools at all. They read evidence the fit matcher already fetched.

The worker and the health probe call `get_events`, `get_policy` and `get_connects_balance` outside any agent. The server-side check that does apply to every caller is the `write` scope on write tools.

## Authentication

- The API mints a signed service token per run (`agent/security.py`): HS256 JWT with audience `gigbid-mcp`, claims `sub`, `tenant`, `persona`, `scopes` (default `read`, `write`) and a one-hour expiry. The signing key is `APP_SECRET`.
- Over HTTP the token goes in `Authorization: Bearer ...`. In process it goes in the request `_meta`. `identity()` in `mcp_servers/common.py` checks `_meta`, then the header, then the in-process context variable.
- `BearerGuard` is an ASGI middleware on the HTTP apps of the three servers. It returns 401 with `www-authenticate: Bearer` when the token is missing or invalid.
- Portfolio: over HTTP it requires a token unless started with `--no-auth`. Over stdio it needs none and uses a local identity `local:<owner>`.
- The health probe mints a token with only the `read` scope.

## Rate limiting

The marketplace server has a sliding-window limiter per user (`RateLimiter` in `mcp_servers/common.py`), set by `marketplace.max_requests_per_minute` (40). It stays under GigSim's own limit of 60 per minute. When the window is full the call waits, at most 5 s, and then goes on. GigSim also returns 429 with `Retry-After`, and the adapter honours it. The portfolio and workspace servers have no limiter.

## Audit log

`common.audit()` writes to the `audit_log` table (a JSON Lines file under `cache/` when there is no database). A row has the server, tool, user, arguments, result, trace id, `dry_run` and `ok`. Arguments and results are PII-masked, and results are cut to 2000 characters. A trigger rejects UPDATE and DELETE.

What is audited:

- Marketplace: every tool call that reaches the adapter, including failures (`ok=false`). `submit_proposal` with `dry_run` is audited. `create_proposal_draft` and `send_message` with `dry_run` return before the adapter and write no row.
- Workspace: `free_slots`, `create_interview_hold`, `create_email_draft`.
- Portfolio: `search_evidence` only.

The trace id comes from the UI request (`X-Trace-Id`) and is carried through the run, the graph metadata, every MCP call and the audit row.

## Degraded mode

If the marketplace cannot be reached, the adapter raises `MarketplaceUnavailable`, the server answers `MARKETPLACE_UNAVAILABLE`, and the gateway raises `MarketplaceDown`. The run is parked as `waiting_marketplace` and the UI shows a banner. Reads that fail with other errors (for example the Risk Assessor asking for a client) are turned into an `error` field in the client data and the analysis continues. See `docs/ARCHITECTURE.md` (failure handling) and `docs/RUNBOOK.md` (drills).
