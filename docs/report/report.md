% GigBid: a multi-agent freelancer copilot
%% Engineering design review for AI-4016 (R&D assignment). Abdul Majeed, 23P-3038. Repository: github.com/Do-Or-D1E/gigbid. Every number in this report is filled in from a file in evals/results/ by docs/report/build_report.py, so it can be traced and regenerated.

# 1. Problem and constraints

A freelancer on a platform like Upwork spends hours reading job feeds, pays Connects to apply, and loses most bids to generic proposals or to clients who were never serious. GigBid takes over the reading, judging and drafting, and leaves every outward action to the freelancer. The rule that shaped the whole design is simple: nothing reaches a client, and no Connects are spent, until the human approves it in the web UI. That rule is enforced by LangGraph `interrupt()` before the submit node, not by a prompt.

What must never be automated: sending a proposal or message, spending Connects, accepting off-platform contact or payment, and claiming experience the portfolio does not show. The autonomy setting can at most auto-skip clearly low-fit jobs.

Budgets declared up front in `agent/config.yaml`: p95 of 40 s per job analysed and 120 s per proposal, and USD 0.002 per job analysed and USD 0.008 per proposal at list prices. The whole project also ran under a hard cap of USD 2 of billed API spend, enforced in `agent/llm.py` before every billed call. Total billed spend at the time of writing was USD {{decisions_main:billed_usd_total_ledger|.2f}} (ledger in `cache/ledger.sqlite`).

Data. The instructor's starter kit was a small illustrative scaffold, so GigSim (the marketplace simulator), three personas and a 600-job dev set with gold labels were built for this project (`docs/DATA_CARD.md`). Market prices are calibrated on real Upwork data from three public Kaggle datasets, and 282 real postings with their real client signals are mixed into GigSim's live job stream. Synthetic and real records are marked (`real: true`, `source`, `license`).

# 2. Architecture

![Bid graph, rendered from agent/graphs/bid_graph.py](docs/images/bid_graph.png){width=9}

**Bid graph** (one thread per job). The Scout hands a job in and screens it for injected text. Job Analyst, Risk Assessor and Fit Matcher then run in parallel through `Send`; reducers on `steps`, `tokens`, `evidence` and `errors` merge their writes. A deterministic decision node turns the three typed reports into bid, watch or skip. For a bid, the Pricing Strategist, Writer, Claim Verifier, Critic (at most two revisions) and Compliance Guard follow, and `prepare_approval` builds the dry-run preview before `human_approval` interrupts. Approve goes to `submit`; edit goes back through Compliance; reject ends the thread with a reason.

**Conversation graph** (one thread per client conversation): read the thread, classify intent (question, negotiation, interview request, scam signal), gather calendar slots or evidence, draft a reply, check it, and interrupt for approval before `send`.

**Marketplace port.** Agents never call GigSim or Upwork. All marketplace access goes through our Marketplace MCP server, which has two adapters behind one interface: `adapters/gigsim.py` and `adapters/upwork_live.py`, chosen by `marketplace.mode`. The live adapter talks to Upwork's official MCP server through `MultiServerMCPClient` with the user's OAuth 2.1 token (PKCE, client-metadata-document client id, tokens Fernet-encrypted at rest). Live mode was implemented but not exercised end to end, because no Upwork account was available; its tool-name map is marked unverified.

**MCP surface.** Three servers of our own built with the official SDK: Portfolio (read only: `search_evidence`, `get_case_study`, `list_skills`, resource templates and prompts), Marketplace (11 read tools and 3 write tools with Pydantic schemas, annotations, idempotency keys and `dry_run`), and Workspace (free slots, tentative holds, email drafts on a local mock). Third-party: the official Upwork MCP server and GitHub's MCP server for repository ingestion. Each agent gets only the tools in its allowlist. HTTP endpoints need a signed service token; every call is rate limited per user and written to an append-only audit log with its trace id (a Postgres trigger rejects UPDATE and DELETE).

**Stores.** State is kept apart from the execution trace and from long-term memory. State (`agent/state.py`) holds what one job needs now. The execution trace (`agent/tracing.py`, the `spans` table and LangSmith) records every model and tool call. Long-term memory lives in a LangGraph store under `("style", user)` and `("outcome", user)` and is only written by the promotion rules in `agent/memory/promotion_rules.py`: a style rule needs the same edit pattern in 2 of the last 5 edits, an outcome insight needs at least 3 finished proposals in a category.

**Why each agent exists.** The Analyst turns messy posts into a JobSpec the Writer and Critic can check against. The Risk Assessor is the only node that reads client history. The Fit Matcher grounds the bid decision in evidence rather than vibes. The decision node is deliberately not an LLM: thresholds in config make every skip explainable. Pricing is separate because it needs live Connects quotes. The Verifier exists because the Writer, left alone, invents experience (section 8). The Critic catches generic openings and missed requirements; Compliance enforces the policy pack and has the power to block.

**Durability.** The Postgres checkpointer stores every step. The `runs` table is the durable queue: claiming is one UPDATE, a run whose heartbeat goes stale is reclaimed and continues from its checkpoint, and submission uses deterministic idempotency keys at both the MCP server and GigSim. The integration test `tests/integration/test_api_flow.py` drives the real API from inbox to approval to submission and checks that a second approval is refused and GigSim holds exactly one proposal. Any checkpoint can be replayed from the run viewer (time travel fork).

# 3. R&D question A: tool granularity

Hypothesis: fewer, coarser tools save tokens but lower argument accuracy; better descriptions on the fine-grained set beat both. Setup: 40 tasks with one known correct call each (`evals/runners/tool_granularity.py`), three designs built from the real MCP schemas, one tool-calling model. The open model on Groq's free tier was too rate limited for this study (the 20-tool schema alone is about 5k tokens per call at an 8k tokens-per-minute limit), so it ran on gpt-4o-mini.

{{table:tools}}

The coarse design cut tokens per task by about 85% but argument accuracy fell to {{tool_granularity_paid:summary.coarse.argument_accuracy|.3f}}: with one `params` object the model kept guessing argument names. Rewriting the descriptions of the fine-grained set (when to use, when not, an example) lifted argument accuracy from {{tool_granularity_paid:summary.fine.argument_accuracy|.3f}} to {{tool_granularity_paid:summary.best.argument_accuracy|.3f}} for about 8% more tokens. Conclusion: granularity changes behaviour, mostly through arguments, not tool choice. The shipped tool set keeps fine-grained tools; the rewritten descriptions are the next change to the servers.

# 4. R&D question B: retrieval, verification and the shipped choice

Hypothesis stated before running: requirement decomposition plus hybrid retrieval would raise evidence recall over V0 on multi-requirement jobs. Variants V0 to V8 are presets of one pipeline (`rag/variants/base.py`), so each is V0 plus one component and the ablation removes one component at a time. Queries are built exactly as the Fit Matcher builds them. Relevance comes from the gold evidence of each dev job (graded 1 or 2). Because jobs have about 16 relevant items, Recall@5 is low by construction; capped recall (hits in the top 5 divided by min(5, relevant)) is reported next to it.

{{table:rag}}

The hypothesis was wrong. Decomposition was the worst variant: one query per listed skill lost the context of the post and merged many weak lists. The big win was multi-vector indexing. Summaries, READMEs and code are indexed separately and returned as whole projects, which finds repos whose README says little and keeps a project's case study, repo and review together. Outcome-aware ranking added MRR. The cross-encoder (V3, measured on a stratified subset of {{rag_ablation:rerank_subset.jobs_per_persona_sampled}} jobs per persona) made ranking worse and added about 2 s of p95 latency: an MS MARCO reranker judges web-question relevance, not "does this project prove this requirement". The LLM variants V6, V7 and V8 were run on a smaller subset because they cost model calls (`evals/results/rag_llm_variants.json`).

Ablation of the shipped pipeline (all dev jobs):

{{table:ablation}}

**Claim verification.** After drafting, the Verifier splits the proposal into claims about past experience, checks each against the evidence, rewrites unsupported ones and, if any remain, deletes the sentences that carry them, then re-verifies. Commitments about the job ("I will...") are not claims. On the main dev run, unsupported claims per proposal fell from {{decisions_main:summary.unsupported_per_proposal_first_draft|.2f}} in the first draft to {{decisions_main:summary.unsupported_per_proposal_final|.2f}} in the version the human sees.

**End to end, V0 against the shipped design** (paired bid jobs, GigSim reset between arms):

{{table:headline}}

The judge is a rubric LLM judge (`agent/prompts/judge.md`). It is reported as uncalibrated until the 30 human labels exist: `evals/label_tool.html` and `uv run python -m evals.runners.judge kappa` produce Cohen's kappa in `evals/results/judge_calibration.json`. The blind pairwise classmate panel was not run.

**Where better retrieval did not mean better replies.** Retrieval nDCG doubled, but the simulated reply probability moved much less. GigSim's clients reward must-have skills that are mentioned and backed by specifics, personalisation, and a non-generic opening, and penalise bids over their budget ceiling. Once the Writer has two or three good items, more good items do not change the letter much. Price matters more: only {{decisions_main:summary.price_in_band|.2f}} of priced bids fell inside the gold fair band, and an over-ceiling bid cuts reply probability by 70% in GigSim.

**Shipped choice.** `hybrid + outcome + multivector`, chosen by nDCG@10 on all dev jobs with the faster pipeline winning ties, and written to `evals/results/rag_decision.json`, which `rag/retriever.py` reads when config says `variant: best`. Reranking is not shipped: it lowered quality and does not fit a serverless function.

# 5. R&D question C: single agent, prebuilt supervisor, hand-built graph

Same 15 dev jobs (5 per persona, stratified), same tools, same model (gpt-4o-mini), same scoring: decisions against gold, unsupported claims with the same verifier and evidence pool, policy violations left in the output, tokens and latency (`evals/runners/multiagent_compare.py`).

{{table:multiagent}}

The hand-built graph decided better and grounded its letters better than the single ReAct agent, and it was the only system that caught a policy violation. The ReAct agent wins on simplicity and on latency for easy jobs: on exact-tool and standard jobs it decided as well as the graph with fewer moving parts and no critique loop. I would ship it for a "quick triage" mode, never for drafting: its letters carried {{multiagent_compare:systems.react.unsupported_per_proposal|.1f}} unsupported claims each and two of them had policy violations. The prebuilt supervisor often ended without a structured answer, which had to be extracted from its final messages; that is a real cost of a prebuilt hand-off protocol.

# 6. The change request

What changed: GigSim's policy v2 (effective 2 Nov) adds a 50% Connects surcharge on jobs with 15 or more proposals and rejects proposals with links other than github.com. What I had to edit: `policy.version: 1 -> 2` in `agent/config.yaml` and the simulator's policy version in `infra/docker-compose.yml`. That is 2 files, 2 insertions and 1 deletion (`git show --stat` on the change-request commit), about ten minutes including the measurement. It was cheap because pricing never hard-codes Connects (it reads the live policy-aware quote) and the Compliance Guard reads the active policy pack. Measured (`evals/results/change_request.json`): mean Connects on busy jobs went from {{change_request:mean_connects_on_busy_jobs_v1}} to {{change_request:mean_connects_on_busy_jobs_v2}}; a letter with a portfolio link was rejected by GigSim under v2 ({{change_request:gigsim_submit.v2_raw_letter.status}} `{{change_request:gigsim_submit.v2_raw_letter.rule}}`) and accepted after the Compliance Guard removed the link.

# 7. Signature extension: X2 proposal experiments

Two writer strategies run as an A/B test in GigSim on the same bid-worthy jobs (paired design, GigSim reset between arms): A is the default evidence-first letter (up to 260 words), B is short (up to 120 words) and opens with one specific question. The strategy is a prompt chosen in config (`writer.prompt`), not code. Primary metric: GigSim's reply probability, tested with a paired sign-flip permutation test; secondary: simulated replies with an exact McNemar test (`evals/results/ab_writer.json`).

{{table:ab}}

# 8. Failure analysis

Every failed job of the main dev run was classified mechanically (`evals/runners/failure_analysis.py`, `evals/results/failure_analysis_main.json`): {{failure_analysis_main:failed_jobs}} of {{failure_analysis_main:jobs}} jobs had at least one failure. Counts by category: mispriced {{failure_analysis_main:by_category.mispriced}}, wrong skip {{failure_analysis_main:by_category.wrong skip}}, compliance block {{failure_analysis_main:by_category.compliance miss}}, unsupported claim left {{failure_analysis_main:by_category.unsupported claim}}, wrong bid {{failure_analysis_main:by_category.wrong bid}}.

- **Unsupported claim** (found in the first end-to-end run). Claims were grounded in past proposals, which are bids, not proof, and Compliance blocked a reasonable draft. Fix: proof-only evidence types for grounding (ADR 0004). Worked: every claim in the next run was backed by a case study or the CV.
- **Unsupported claim, loop that never converged.** The Verifier counted "I will..." plans as unsupported, so the Critic sent drafts back three times. Fix: a plan filter (ADR 0007). Worked.
- **Compliance miss turned block.** The Writer invented cross-validation and grid-search experience, the Critic asked for missing requirements to be covered, and Compliance correctly blocked. Fix: the Verifier deletes sentences that still carry unsupported claims, and the Critic is told which requirements have no evidence. Partly worked: blocks fell but {{failure_analysis_main:by_category.compliance miss}} drafts were still blocked in the main run.
- **Mispriced.** The largest category. The Pricing Strategist anchors on the client's budget and the freelancer's floor, while the gold fair band comes from the market; the floor of an experienced persona often sits above the band. Not fixed: it is partly a persona decision, and the report keeps it visible rather than tuning to the band.
- **Wrong skip.** Mostly the Risk Assessor scoring new, unverified clients as risky, and the Fit Matcher under-scoring vague posts. Not fixed.
- **Injection over-blocking.** With defences on, decisions on injected jobs were worse than with defences off (F1 {{decisions_inj_on:summary.bid_skip.f1|.2f}} against {{decisions_inj_off:summary.bid_skip.f1|.2f}}): flagged injected text pushed risk up, so good jobs were skipped. Fix: injection flags alone are capped in the decision node. Re-run as `decisions_inj_on_fixed.json`: F1 {{decisions_inj_on_fixed:summary.bid_skip.f1|.2f}}.
- **Injection, inserted phrase.** Two attacks made the Writer insert a planted phrase. Fix: an echo guard in Compliance removes any phrase the post's suspicious instructions asked to insert. Re-run: attack success {{decisions_inj_on_fixed:summary.injection_attack_success_rate|.2f}}.
- **Tool errors** (fixed during development): GigSim's screening answers are strings while the port carried question and answer objects (422 on every submission); and the Connects quote field was named differently. Both were fixed in the adapter, which is where marketplace shapes belong.

# 9. Safety and platform respect

GigBid must never send without approval, spend Connects silently, move a client off-platform, invent experience, or scrape. Enforcement is layered: the interrupt before submit and send; write tools that need an idempotency key and a write scope and offer `dry_run`; the Compliance Guard with a deterministic pass that cannot be overruled (contact details, guarantees, disallowed links) plus a model pass; job posts and client messages wrapped as untrusted data with fake tags neutralised; a pattern screen whose hits go to the Risk Assessor; PII masking in logs, traces and the audit log; tenant scoping on every query; Fernet-encrypted OAuth tokens. Live mode only creates drafts that the user confirms on Upwork, uses no browser automation or cookies, and polls no more often than every 240 minutes.

Injection, measured on 21 planted-injection dev jobs: attack success {{decisions_inj_off:summary.injection_attack_success_rate|.2f}} with defences off, {{decisions_inj_on:summary.injection_attack_success_rate|.2f}} with them on before the fixes, {{decisions_inj_on_fixed:summary.injection_attack_success_rate|.2f}} after.

{{table:injection}}

What still gets through: an attack that asks for something the policy allows (for example "mention our CRM name twice") is indistinguishable from a client request; a scam that only reveals itself in a later message is caught by the Liaison's intent classifier, not before bidding; and the Upwork live path was not tested against the real server.

# 10. Hidden test results against the declared budgets

The instructor's hidden run happens on the deployed link after submission, so it is not in this report. As a stand-in, a held-out set generated with an unseen seed (never used for tuning, git-ignored) was run through the same system. Measured against the declared budgets:

| Metric | Declared | Dev (main run) | Held-out run |
|---|---|---|---|
| p95 s per job analysed | 40 | {{decisions_main:summary.latency_s.p95_job_analysed|.1f}} | {{decisions_holdout:summary.latency_s.p95_job_analysed|.1f}} |
| p95 s per proposal | 120 | {{decisions_main:summary.latency_s.p95_proposal|.1f}} | {{decisions_holdout:summary.latency_s.p95_proposal|.1f}} |
| USD per job analysed (list) | 0.002 | {{decisions_main:summary.cost_usd_list.per_job_analysed|.4f}} | {{decisions_holdout:summary.cost_usd_list.per_job_analysed|.4f}} |
| USD per proposal (list) | 0.008 | {{decisions_main:summary.cost_usd_list.per_proposal|.4f}} | {{decisions_holdout:summary.cost_usd_list.per_proposal|.4f}} |
| Bid/skip F1 | | {{decisions_main:summary.bid_skip.f1|.3f}} | {{decisions_holdout:summary.bid_skip.f1|.3f}} |

Cost met the budget. Latency per proposal did not, by a wide margin. A proposal is about {{decisions_main:summary.tokens_per_proposal|.0f}} tokens over roughly 25 sequential model calls, most of them in the verify and critique loop, and the dev runs shared one API key across several parallel evaluations. The optimisation that helped most was making claim verification converge (plan filter and sentence removal): it cut critique rounds and blocked drafts. The next one is to verify once per round instead of twice, and to stop the Critic loop when only style issues remain.

**Open models.** The deployed app runs the `open` profile (gpt-oss-20b and gpt-oss-120b on Groq). On a 12-job comparison of two open configurations, Groq's free tier (8k tokens per minute per model) caused node timeouts on {{decisions_open:summary.errors}} and {{decisions_open_qwen:summary.errors}} of 12 jobs, which is the main reason the large evaluations ran on gpt-4o-mini. Both open configurations decided correctly on most of the jobs they finished (`decisions_open.json`, `decisions_open_qwen.json`); the comparison is too small to rank them.

# Appendix: what is not done

The 30 human judge labels and the classmate panel need the student; live Upwork mode was not exercised; the demo video and the public write-up are the student's to publish. Everything else in this report can be regenerated with `make eval` and `uv run python docs/report/build_report.py`.
