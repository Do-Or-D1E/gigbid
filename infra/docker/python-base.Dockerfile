# Shared base for every Python service (API, worker, GigSim, MCP servers).
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_SYSTEM_PYTHON=1 GIGBID_MODEL_DIR=/models
RUN pip install --no-cache-dir uv==0.9.5
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv export --frozen --no-dev --no-hashes -o requirements.txt && uv pip install --system -r requirements.txt
COPY agent agent
COPY apps/api apps/api
COPY apps/__init__.py apps/__init__.py
COPY rag rag
COPY mcp_servers mcp_servers
COPY gigsim gigsim
COPY worker worker
COPY data data
COPY evals/__init__.py evals/__init__.py
COPY evals/results/rag_decision.json evals/results/rag_decision.json
