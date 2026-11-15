# Standalone, publishable Portfolio MCP server (stdio by default, for Claude Desktop / Cursor):
#   docker run -i --rm ghcr.io/do-or-d1e/gigbid-portfolio-mcp --owner ai_ml
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 GIGBID_MODEL_DIR=/models
RUN pip install --no-cache-dir uv==0.9.5
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv export --frozen --no-dev --no-hashes -o requirements.txt && uv pip install --system -r requirements.txt
COPY agent agent
COPY rag rag
COPY mcp_servers mcp_servers
COPY data/personas data/personas
COPY data/taxonomy.json data/taxonomy.json
COPY evals/results/rag_decision.json evals/results/rag_decision.json
RUN python -c "from rag.index.embeddings import get_embedder; get_embedder()"
ENV APP_SECRET=standalone-not-used-for-stdio-0123456789
ENTRYPOINT ["python", "-m", "mcp_servers.portfolio.server", "--stdio"]
