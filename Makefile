# GigBid. Python via uv, web via npm. `make dev` runs everything locally without Docker.
.PHONY: dev test eval seed demo lint smoke api worker mcp gigsim compose data

PY := uv run python

dev:            ## API (GigSim + MCP mounted in-process) and the web dev server
	INPROC_SERVICES=1 MCP_TRANSPORT=inproc GIGSIM_BASE_URL=inproc uv run uvicorn apps.api.main:app --port 8000 & \
	cd apps/web && npm run dev

api:
	uv run uvicorn apps.api.main:app --reload --port 8000

worker:
	uv run arq worker.arq_worker.WorkerSettings

gigsim:
	uv run uvicorn gigsim.app:app --port 8081

mcp:
	$(PY) -m mcp_servers.portfolio.server --port 8101 & $(PY) -m mcp_servers.marketplace.server --port 8102 & \
	$(PY) -m mcp_servers.workspace.server --port 8103

compose:
	docker compose -f infra/docker-compose.yml up --build

test:           ## unit, contract, MCP, GigSim and data tests + web e2e
	uv run pytest -q tests/unit tests/contract tests/gigsim mcp_servers
	cd apps/web && npm run test:e2e

lint:
	uv run ruff check agent apps/api rag mcp_servers worker --select E9,F63,F7,F82
	$(PY) scripts/check_prompts.py
	$(PY) scripts/gigsim_checksums.py --verify
	$(PY) scripts/check_numbers.py

data:           ## regenerate synthetic data (real Kaggle samples must already be in data/real)
	$(PY) scripts/generate_data.py

seed:           ## reviewer user, saved search and analysed jobs in the running stack
	$(PY) scripts/seed_demo.py

eval:           ## retrieval, decisions and GigSim reply rate; writes evals/results/*.json
	$(PY) -m evals.runners.rag_eval
	$(PY) -m evals.runners.ablation
	$(PY) -m evals.runners.decision_eval --n 20 --tag main --submit
	$(PY) -m evals.runners.make_tables

smoke:          ## 30-job smoke eval with failure thresholds (CI)
	$(PY) -m evals.runners.smoke_eval --n 10

demo:           ## one job from inbox to the approval gate, printed in the terminal
	$(PY) scripts/demo_one_job.py
