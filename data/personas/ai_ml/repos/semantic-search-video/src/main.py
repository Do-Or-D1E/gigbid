from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import psycopg


DDL = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS chunks (
    id bigserial PRIMARY KEY,
    doc_id text NOT NULL,
    body text NOT NULL,
    embedding vector(384)
);
CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks USING hnsw (embedding vector_cosine_ops);
"""


def nearest(conn, query_vec, k=5):
    sql = "SELECT doc_id, body, embedding <=> %s::vector AS dist FROM chunks ORDER BY dist LIMIT %s"
    with conn.cursor() as cur:
        cur.execute(sql, (str(list(query_vec)), k))
        return cur.fetchall()


_model = SentenceTransformer("all-MiniLM-L6-v2")


def embed(texts: list[str], batch_size: int = 64):
    return _model.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                         show_progress_bar=False).tolist()


app = FastAPI(title="Article service", version="1.3.0")


class ScoreRequest(BaseModel):
    article_id: str
    features: dict[str, float]


class ScoreResponse(BaseModel):
    score: float
    model_version: str


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/score", response_model=ScoreResponse)
def score(req: ScoreRequest):
    if not req.features:
        raise HTTPException(status_code=422, detail="features must not be empty")
    return ScoreResponse(score=0.5, model_version="2024-05-14")
