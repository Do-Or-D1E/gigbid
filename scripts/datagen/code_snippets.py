"""Code snippet bank used to assemble real-looking repo source files.

Each entry: skill -> list of dicts(lang, file, imports, body, reveals).
Tokens @ent@, @Ent@, @table@ are replaced per project.  `reveals` lists all taxonomy skills that the
snippet visibly uses (own skill included); a snippet is only used when reveals is a subset of the
project's skills (plus the base languages).
"""
from __future__ import annotations

S = {}


def add(skill, lang, file, imports, body, reveals=None, for_=None):
    S.setdefault(skill, []).append(dict(lang=lang, file=file, imports=imports, body=body.strip("\n"),
                                       reveals=reveals or [skill], for_=for_))


# ------------------------------------------------------------------ python / ml
add("PyTorch", "py", "train.py", ["import torch", "from torch import nn"], '''
class @Ent@Net(nn.Module):
    def __init__(self, n_in: int, n_hidden: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_in, n_hidden), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(n_hidden, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


def train_epoch(model, loader, opt, device="cuda"):
    model.train()
    total = 0.0
    for xb, yb in loader:
        xb, yb = xb.to(device), yb.to(device)
        opt.zero_grad()
        loss = nn.functional.binary_cross_entropy_with_logits(model(xb), yb)
        loss.backward()
        opt.step()
        total += loss.item() * len(xb)
    return total / len(loader.dataset)
''')

add("scikit-learn", "py", "model.py",
    ["from sklearn.compose import ColumnTransformer", "from sklearn.ensemble import RandomForestClassifier",
     "from sklearn.model_selection import GridSearchCV", "from sklearn.pipeline import Pipeline",
     "from sklearn.preprocessing import OneHotEncoder, StandardScaler"], '''
def build_pipeline(num_cols, cat_cols):
    pre = ColumnTransformer([
        ("num", StandardScaler(), num_cols),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
    ])
    return Pipeline([("pre", pre), ("clf", RandomForestClassifier(random_state=7, n_jobs=-1))])


def tune(pipe, X, y):
    grid = {"clf__n_estimators": [200, 400], "clf__max_depth": [8, 16, None]}
    search = GridSearchCV(pipe, grid, scoring="f1", cv=5)
    search.fit(X, y)
    return search.best_estimator_, search.best_score_
''')

add("XGBoost", "py", "boost.py", ["import xgboost as xgb"], '''
PARAMS = {
    "objective": "binary:logistic",
    "eval_metric": "aucpr",
    "max_depth": 6,
    "eta": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
}


def fit_booster(X_train, y_train, X_val, y_val):
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dval = xgb.DMatrix(X_val, label=y_val)
    return xgb.train(PARAMS, dtrain, num_boost_round=1200, evals=[(dval, "val")],
                     early_stopping_rounds=50, verbose_eval=100)
''', reveals=["XGBoost"])

add("Hugging Face Transformers", "py", "encode.py",
    ["from transformers import AutoModelForSequenceClassification, AutoTokenizer", "import torch"], '''
MODEL_ID = "distilbert-base-uncased"
tok = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID, num_labels=6)


@torch.no_grad()
def predict(texts, batch_size=32):
    out = []
    for i in range(0, len(texts), batch_size):
        batch = tok(texts[i:i + batch_size], truncation=True, padding=True, max_length=256,
                    return_tensors="pt")
        logits = model(**batch).logits
        out.extend(logits.softmax(-1).argmax(-1).tolist())
    return out
''', reveals=["Hugging Face Transformers", "PyTorch"])

add("LangChain", "py", "chain.py",
    ["from langchain_core.output_parsers import StrOutputParser", "from langchain_core.prompts import ChatPromptTemplate",
     "from langchain_openai import ChatOpenAI"], '''
prompt = ChatPromptTemplate.from_messages([
    ("system", "You answer using only the context. If the context is not enough, say so."),
    ("human", "Context:\\n{context}\\n\\nQuestion: {question}"),
])
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
chain = prompt | llm | StrOutputParser()


def answer(question: str, docs: list[str]) -> str:
    return chain.invoke({"context": "\\n---\\n".join(docs), "question": question})
''', reveals=["LangChain", "OpenAI API"])

add("LangGraph", "py", "graph.py",
    ["from typing import TypedDict", "from langgraph.checkpoint.memory import MemorySaver",
     "from langgraph.graph import END, StateGraph"], '''
class State(TypedDict):
    question: str
    sources: list[str]
    draft: str
    approved: bool


def build_graph(search, write, review):
    g = StateGraph(State)
    g.add_node("search", search)
    g.add_node("write", write)
    g.add_node("review", review)
    g.set_entry_point("search")
    g.add_edge("search", "write")
    g.add_edge("write", "review")
    g.add_conditional_edges("review", lambda s: END if s["approved"] else "write")
    return g.compile(checkpointer=MemorySaver(), interrupt_before=["review"])
''')

add("RAG", "py", "retrieve.py", ["import math", "from collections import defaultdict"], '''
def chunk(text: str, size: int = 400, overlap: int = 60) -> list[str]:
    words = text.split()
    step = size - overlap
    return [" ".join(words[i:i + size]) for i in range(0, max(len(words) - overlap, 1), step)]


def cosine(a, b):
    num = sum(x * y for x, y in zip(a, b))
    den = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return num / den if den else 0.0


def top_k(query_vec, index, k=5):
    scored = [(cosine(query_vec, vec), doc_id, text) for doc_id, vec, text in index]
    return sorted(scored, reverse=True)[:k]


def build_prompt(question, hits):
    cited = "\\n".join(f"[{i + 1}] {t}" for i, (_, _, t) in enumerate(hits))
    return f"Answer from the numbered passages only and cite them.\\n{cited}\\n\\nQ: {question}"
''')

add("Pinecone", "py", "index.py", ["import os", "from pinecone import Pinecone"], '''
pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
index = pc.Index("@table@-docs")


def upsert_batch(rows, namespace="prod"):
    vectors = [
        {"id": r["id"], "values": r["embedding"], "metadata": {"source": r["source"], "page": r["page"]}}
        for r in rows
    ]
    index.upsert(vectors=vectors, namespace=namespace)


def search(vec, k=8, source=None):
    flt = {"source": {"$eq": source}} if source else None
    res = index.query(vector=vec, top_k=k, include_metadata=True, filter=flt, namespace="prod")
    return [(m.score, m.metadata) for m in res.matches]
''')

add("pgvector", "py", "vectors.py", ["import psycopg"], '''
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
''', reveals=["pgvector"])

add("OpenAI API", "py", "llm.py", ["import json", "from openai import OpenAI"], '''
client = OpenAI()

TOOLS = [{
    "type": "function",
    "function": {
        "name": "check_availability",
        "description": "Check live availability for a date range",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}, "start": {"type": "string"}, "end": {"type": "string"}},
            "required": ["city", "start", "end"],
        },
    },
}]


def ask(messages):
    resp = client.chat.completions.create(model="gpt-4o-mini", messages=messages, tools=TOOLS,
                                          response_format=None, temperature=0.2)
    return resp.choices[0].message
''')

add("MLflow", "py", "track.py", ["import mlflow"], '''
mlflow.set_tracking_uri("http://mlflow:5000")
mlflow.set_experiment("@table@-nightly")


def log_run(params: dict, metrics: dict, model_path: str, promote: bool = False):
    with mlflow.start_run() as run:
        mlflow.log_params(params)
        for name, value in metrics.items():
            mlflow.log_metric(name, value)
        mlflow.log_artifact(model_path)
        if promote:
            mlflow.register_model(f"runs:/{run.info.run_id}/model", "@ent@-model")
        return run.info.run_id
''')

add("AWS SageMaker", "py", "deploy_endpoint.py", ["import boto3", "import sagemaker", "from sagemaker.huggingface import HuggingFaceModel"], '''
role = "arn:aws:iam::123456789012:role/sagemaker-exec"
session = sagemaker.Session(boto_session=boto3.Session(region_name="eu-west-1"))

model = HuggingFaceModel(
    model_data="s3://@table@-models/tagger/model.tar.gz",
    role=role,
    transformers_version="4.37",
    pytorch_version="2.1",
    py_version="py310",
    sagemaker_session=session,
)

predictor = model.deploy(initial_instance_count=1, instance_type="ml.g4dn.xlarge",
                         endpoint_name="@ent@-tagger-prod")
''', reveals=["AWS SageMaker", "Hugging Face Transformers", "AWS"])

add("FastAPI", "py", "api.py", ["from fastapi import FastAPI, HTTPException", "from pydantic import BaseModel"], '''
app = FastAPI(title="@Ent@ service", version="1.3.0")


class ScoreRequest(BaseModel):
    @ent@_id: str
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
''')

add("Celery", "py", "tasks.py", ["from celery import Celery"], '''
app = Celery("@table@", broker="redis://redis:6379/0", backend="redis://redis:6379/1")
app.conf.task_acks_late = True
app.conf.worker_prefetch_multiplier = 1


@app.task(bind=True, autoretry_for=(ConnectionError,), retry_backoff=True, max_retries=5)
def process_@ent@(self, @ent@_id: str):
    payload = fetch_@ent@(@ent@_id)
    result = analyse(payload)
    store_result(@ent@_id, result)
    return {"id": @ent@_id, "ok": True}


@app.task
def nightly_sweep():
    for @ent@_id in pending_ids():
        process_@ent@.delay(@ent@_id)
''', reveals=["Celery"])

add("Redis", "py", "cache.py", ["import json", "import redis"], '''
r = redis.Redis(host="redis", port=6379, decode_responses=True)


def cached_features(@ent@_id: str, builder, ttl: int = 300):
    key = f"feat:{@ent@_id}"
    hit = r.get(key)
    if hit:
        return json.loads(hit)
    feats = builder(@ent@_id)
    r.setex(key, ttl, json.dumps(feats))
    return feats


def allow(client_ip: str, limit: int = 60) -> bool:
    key = f"rl:{client_ip}"
    n = r.incr(key)
    if n == 1:
        r.expire(key, 60)
    return n <= limit
''')

add("Airflow", "py", "dags/nightly.py", ["from datetime import datetime, timedelta", "from airflow import DAG",
                                         "from airflow.operators.python import PythonOperator"], '''
default_args = {"owner": "data", "retries": 3, "retry_delay": timedelta(minutes=10)}

with DAG(
    dag_id="@table@_nightly",
    start_date=datetime(2024, 1, 1),
    schedule="0 2 * * *",
    catchup=False,
    default_args=default_args,
) as dag:
    extract = PythonOperator(task_id="extract", python_callable=extract_@table@)
    transform = PythonOperator(task_id="transform", python_callable=transform_@table@)
    load = PythonOperator(task_id="load", python_callable=load_@table@)
    extract >> transform >> load
''')

add("pandas", "py", "clean.py", ["import pandas as pd"], '''
def load_@table@(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", dayfirst=True)
    df["amount"] = pd.to_numeric(df["amount"].str.replace(",", ""), errors="coerce")
    df = df.dropna(subset=["created_at"]).drop_duplicates(subset=["@ent@_id"])
    return df


def monthly(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby(df["created_at"].dt.to_period("M"))["amount"]
              .agg(["count", "sum", "mean"]).reset_index())
''')

add("NumPy", "py", "arrays.py", ["import numpy as np"], '''
def normalise(batch: np.ndarray) -> np.ndarray:
    mean = batch.mean(axis=(0, 1, 2), keepdims=True)
    std = batch.std(axis=(0, 1, 2), keepdims=True) + 1e-6
    return (batch - mean) / std


def iou(a: np.ndarray, b: np.ndarray) -> float:
    x1, y1 = np.maximum(a[:2], b[:2])
    x2, y2 = np.minimum(a[2:], b[2:])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = np.prod(a[2:] - a[:2]) + np.prod(b[2:] - b[:2]) - inter
    return float(inter / union) if union else 0.0
''')

add("OCR", "py", "scan.py", ["import re", "import pytesseract", "from PIL import Image, ImageOps"], '''
AMOUNT = re.compile(r"(?:total|amount due)[^0-9]{0,12}([0-9][0-9,]*\\.[0-9]{2})", re.I)


def read_page(path: str) -> str:
    img = ImageOps.autocontrast(Image.open(path).convert("L"))
    return pytesseract.image_to_string(img, config="--psm 6")


def find_total(text: str):
    m = AMOUNT.search(text)
    return float(m.group(1).replace(",", "")) if m else None
''')

add("named entity recognition", "py", "entities.py", ["import spacy"], '''
nlp = spacy.load("en_core_web_trf", disable=["lemmatizer"])
KEEP = {"ORG", "PERSON", "GPE", "MONEY", "DATE"}


def extract_entities(text: str) -> dict[str, list[str]]:
    doc = nlp(text)
    found: dict[str, list[str]] = {}
    for ent in doc.ents:
        if ent.label_ in KEEP:
            found.setdefault(ent.label_, []).append(ent.text.strip())
    return {k: sorted(set(v)) for k, v in found.items()}
''')

add("computer vision", "py", "detect.py", ["import cv2"], '''
def preprocess(path: str, size=(640, 640)):
    img = cv2.imread(path)
    img = cv2.resize(img, size)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img


def find_blobs(img, thresh=40):
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, mask = cv2.threshold(blur, thresh, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return [cv2.boundingRect(c) for c in contours if cv2.contourArea(c) > 120]
''')

add("time-series forecasting", "py", "forecast.py", ["import math"], '''
def seasonal_naive(history: list[float], season: int = 7, horizon: int = 7):
    return [history[-season + (h % season)] for h in range(horizon)]


def holt_winters(history, season=7, alpha=0.3, beta=0.05, gamma=0.2, horizon=7):
    level, trend = history[0], history[1] - history[0]
    seasonal = [history[i] - level for i in range(season)]
    for t, y in enumerate(history):
        s = seasonal[t % season]
        last = level
        level = alpha * (y - s) + (1 - alpha) * (level + trend)
        trend = beta * (level - last) + (1 - beta) * trend
        seasonal[t % season] = gamma * (y - level) + (1 - gamma) * s
    return [level + (h + 1) * trend + seasonal[(len(history) + h) % season] for h in range(horizon)]


def wape(actual, pred):
    return sum(abs(a - p) for a, p in zip(actual, pred)) / max(sum(abs(a) for a in actual), 1e-9)
''')

add("embeddings", "py", "embed.py", ["from sentence_transformers import SentenceTransformer"], '''
_model = SentenceTransformer("all-MiniLM-L6-v2")


def embed(texts: list[str], batch_size: int = 64):
    return _model.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                         show_progress_bar=False).tolist()
''')

add("fine-tuning", "py", "lora.py",
    ["from peft import LoraConfig, get_peft_model", "from transformers import AutoModelForCausalLM, Trainer, TrainingArguments"], '''
def make_trainer(base_id, train_ds, eval_ds, out_dir="out/lora"):
    model = AutoModelForCausalLM.from_pretrained(base_id)
    cfg = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, target_modules=["q_proj", "v_proj"],
                     task_type="CAUSAL_LM")
    model = get_peft_model(model, cfg)
    args = TrainingArguments(output_dir=out_dir, num_train_epochs=3, per_device_train_batch_size=8,
                             learning_rate=2e-4, evaluation_strategy="epoch", logging_steps=25)
    return Trainer(model=model, args=args, train_dataset=train_ds, eval_dataset=eval_ds)
''', reveals=["fine-tuning", "Hugging Face Transformers"])

add("LLM evaluation", "py", "evals/run_evals.py", ["import json", "import statistics"], '''
RUBRIC = "Score 1-5 for factual accuracy, 1-5 for completeness. Reply as JSON: {\\"acc\\": n, \\"comp\\": n}."


def judge(call_model, question, reference, answer):
    reply = call_model(f"{RUBRIC}\\nQ: {question}\\nReference: {reference}\\nAnswer: {answer}")
    return json.loads(reply)


def run_suite(cases, call_model, answer_fn, floor=4.0):
    scores = []
    for case in cases:
        ans = answer_fn(case["question"])
        s = judge(call_model, case["question"], case["reference"], ans)
        scores.append((s["acc"] + s["comp"]) / 2)
    mean = statistics.mean(scores)
    print(f"mean={mean:.2f} n={len(scores)}")
    assert mean >= floor, "prompt regression: mean score below floor"
''')

add("anomaly detection", "py", "anomaly.py", ["import statistics"], '''
def robust_z(values: list[float]) -> list[float]:
    med = statistics.median(values)
    mad = statistics.median(abs(v - med) for v in values) or 1e-9
    return [0.6745 * (v - med) / mad for v in values]


def flag(window: list[float], threshold: float = 3.5) -> list[int]:
    scores = robust_z(window)
    return [i for i, z in enumerate(scores) if abs(z) > threshold]
''')

add("recommendation systems", "py", "recs.py", ["from collections import Counter, defaultdict", "import math"], '''
def build_cooccurrence(baskets: list[list[str]]):
    co = defaultdict(Counter)
    for basket in baskets:
        for a in basket:
            for b in basket:
                if a != b:
                    co[a][b] += 1
    return co


def recommend(co, seen: list[str], k: int = 5):
    scores = Counter()
    for item in seen:
        total = sum(co[item].values()) or 1
        for other, n in co[item].items():
            if other not in seen:
                scores[other] += n / math.sqrt(total)
    return [i for i, _ in scores.most_common(k)]
''')

add("feature engineering", "py", "features.py", ["from collections import defaultdict, deque"], '''
def rolling_features(events, window=30):
    """events: iterable of dicts sorted by ts with keys @ent@_id, ts, value."""
    buf = defaultdict(lambda: deque(maxlen=window))
    out = []
    for e in events:
        hist = buf[e["@ent@_id"]]
        vals = [h["value"] for h in hist]
        out.append({
            "@ent@_id": e["@ent@_id"],
            "ts": e["ts"],
            "n_prev": len(vals),
            "mean_prev": sum(vals) / len(vals) if vals else 0.0,
            "max_prev": max(vals) if vals else 0.0,
            "gap_days": (e["ts"] - hist[-1]["ts"]).days if hist else -1,
        })
        hist.append(e)
    return out
''')

add("text classification", "py", "classify.py", ["import re", "from collections import Counter, defaultdict", "import math"], '''
TOKEN = re.compile(r"[a-z0-9']+")


class NaiveBayes:
    def __init__(self):
        self.words = defaultdict(Counter)
        self.docs = Counter()

    def fit(self, texts, labels):
        for t, y in zip(texts, labels):
            self.docs[y] += 1
            self.words[y].update(TOKEN.findall(t.lower()))

    def predict(self, text):
        toks = TOKEN.findall(text.lower())
        best, best_lp = None, -1e18
        for y, n in self.docs.items():
            total = sum(self.words[y].values()) + len(self.words[y]) + 1
            lp = math.log(n / sum(self.docs.values()))
            lp += sum(math.log((self.words[y][w] + 1) / total) for w in toks)
            if lp > best_lp:
                best, best_lp = y, lp
        return best
''')

add("model deployment", "py", "serve/smoke_test.py", ["import subprocess", "import sys"], '''
def smoke_test(url: str) -> None:
    out = subprocess.run(["curl", "-sf", f"{url}/healthz"], capture_output=True, text=True)
    if out.returncode != 0:
        print("health check failed", out.stderr)
        sys.exit(1)
    print("healthy:", out.stdout.strip())


def canary_ok(old_p95_ms: float, new_p95_ms: float, tolerance: float = 1.15) -> bool:
    return new_p95_ms <= old_p95_ms * tolerance
''')

add("Docker", "docker", "Dockerfile", [], '''
# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# dependencies first so the layer is cached between code changes
FROM base AS deps
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

FROM base AS runtime
COPY --from=deps /install /usr/local
COPY . .
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost:8000/healthz || exit 1
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
''', for_=("ai_ml", "data_analyst"))
add("Docker", "docker", "Dockerfile", [], '''
# syntax=docker/dockerfile:1
FROM node:20-alpine AS build
WORKDIR /app

# install dependencies with a clean lockfile install
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build && npm prune --omit=dev

FROM node:20-alpine AS runtime
ENV NODE_ENV=production
WORKDIR /app
COPY --from=build /app/dist ./dist
COPY --from=build /app/node_modules ./node_modules
COPY package.json ./

USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost:3000/healthz || exit 1
CMD ["node", "dist/server.js"]
''', for_=("fullstack",))
add("Docker", "yaml", "docker-compose.yml", [], '''
services:
  app:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: example
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      retries: 10
    volumes:
      - dbdata:/var/lib/postgresql/data
volumes:
  dbdata:
''')

add("AWS", "py", "storage.py", ["import boto3"], '''
s3 = boto3.client("s3", region_name="eu-west-1")
BUCKET = "@table@-uploads-prod"


def presign_upload(key: str, content_type: str, expires: int = 900) -> str:
    return s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": BUCKET, "Key": key, "ContentType": content_type},
        ExpiresIn=expires,
    )


def latest_object(prefix: str):
    resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix)
    items = sorted(resp.get("Contents", []), key=lambda o: o["LastModified"])
    return items[-1]["Key"] if items else None
''')

add("PostgreSQL", "py", "db.py", ["import psycopg"], '''
def connect(dsn: str):
    return psycopg.connect(dsn, autocommit=False)


def upsert_@table@(conn, rows):
    sql = """
        INSERT INTO @table@ (@ent@_id, status, amount, updated_at)
        VALUES (%(@ent@_id)s, %(status)s, %(amount)s, now())
        ON CONFLICT (@ent@_id) DO UPDATE
        SET status = EXCLUDED.status, amount = EXCLUDED.amount, updated_at = now()
    """
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    conn.commit()
''')

add("Django", "py", "app/models.py", ["from django.db import models"], '''
class @Ent@(models.Model):
    STATUS = [("new", "New"), ("paid", "Paid"), ("cancelled", "Cancelled")]

    reference = models.CharField(max_length=24, unique=True)
    owner = models.ForeignKey("auth.User", on_delete=models.PROTECT, related_name="@table@")
    status = models.CharField(max_length=12, choices=STATUS, default="new", db_index=True)
    total_cents = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["owner", "status"])]

    def __str__(self):
        return f"{self.reference} ({self.status})"
''')
add("Django", "py", "app/views.py", ["from rest_framework import permissions, viewsets",
                                     "from .models import @Ent@", "from .serializers import @Ent@Serializer"], '''
class @Ent@ViewSet(viewsets.ModelViewSet):
    serializer_class = @Ent@Serializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = @Ent@.objects.filter(owner=self.request.user).select_related("owner")
        status = self.request.query_params.get("status")
        return qs.filter(status=status) if status else qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
''')

# analyst / python
add("A/B testing", "py", "experiment.py", ["from math import sqrt", "from scipy.stats import norm"], '''
def two_proportion_z(conv_a, n_a, conv_b, n_b):
    p_a, p_b = conv_a / n_a, conv_b / n_b
    pooled = (conv_a + conv_b) / (n_a + n_b)
    se = sqrt(pooled * (1 - pooled) * (1 / n_a + 1 / n_b))
    z = (p_b - p_a) / se
    return {"lift": p_b / p_a - 1, "z": z, "p_value": 2 * (1 - norm.cdf(abs(z)))}


def sample_size(base_rate, mde, alpha=0.05, power=0.8):
    p1, p2 = base_rate, base_rate * (1 + mde)
    za, zb = norm.ppf(1 - alpha / 2), norm.ppf(power)
    var = p1 * (1 - p1) + p2 * (1 - p2)
    return int(((za + zb) ** 2 * var) / (p2 - p1) ** 2) + 1
''')
add("statistics", "py", "stats_utils.py", ["import random", "import statistics"], '''
def bootstrap_ci(values, stat=statistics.mean, n=5000, alpha=0.05, seed=11):
    rng = random.Random(seed)
    draws = sorted(stat([rng.choice(values) for _ in values]) for _ in range(n))
    return draws[int(n * alpha / 2)], draws[int(n * (1 - alpha / 2)) - 1]


def cohens_d(a, b):
    na, nb = len(a), len(b)
    pooled = (((na - 1) * statistics.variance(a)) + ((nb - 1) * statistics.variance(b))) / (na + nb - 2)
    return (statistics.mean(b) - statistics.mean(a)) / pooled ** 0.5
''')
add("regression analysis", "py", "drivers.py", ["import pandas as pd", "import statsmodels.formula.api as smf"], '''
def fit_price_model(df: pd.DataFrame):
    model = smf.ols("log_rent ~ bedrooms + C(district) + dist_to_station + has_parking", data=df).fit()
    summary = model.summary2().tables[1][["Coef.", "P>|t|"]]
    return model, summary.sort_values("Coef.", ascending=False)
''', reveals=["regression analysis", "pandas"])
add("cohort analysis", "py", "cohorts.py", ["import pandas as pd"], '''
def retention_table(events: pd.DataFrame) -> pd.DataFrame:
    events = events.copy()
    events["cohort"] = events.groupby("user_id")["ts"].transform("min").dt.to_period("M")
    events["age"] = (events["ts"].dt.to_period("M") - events["cohort"]).apply(lambda p: p.n)
    counts = events.groupby(["cohort", "age"])["user_id"].nunique().unstack(fill_value=0)
    return counts.div(counts[0], axis=0).round(3)
''', reveals=["cohort analysis", "pandas"])
add("customer segmentation", "py", "rfm.py", ["import pandas as pd"], '''
def rfm_segments(orders: pd.DataFrame, today: pd.Timestamp) -> pd.DataFrame:
    g = orders.groupby("customer_id").agg(
        recency=("order_date", lambda s: (today - s.max()).days),
        frequency=("order_id", "nunique"),
        monetary=("amount", "sum"),
    )
    g["r"] = pd.qcut(g["recency"], 4, labels=[4, 3, 2, 1]).astype(int)
    g["f"] = pd.qcut(g["frequency"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
    g["m"] = pd.qcut(g["monetary"], 4, labels=[1, 2, 3, 4]).astype(int)
    g["segment"] = g["r"].astype(str) + g["f"].astype(str) + g["m"].astype(str)
    return g
''', reveals=["customer segmentation", "pandas"])
add("data cleaning", "py", "cleanup.py", ["import re", "import pandas as pd"], '''
def clean_names(s: pd.Series) -> pd.Series:
    return (s.str.strip().str.lower().str.replace(r"\\s+", " ", regex=True)
              .str.replace(r"[^a-z0-9 &'-]", "", regex=True))


def dedupe(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    df = df.sort_values("updated_at").drop_duplicates(subset=keys, keep="last")
    df["phone"] = df["phone"].astype(str).str.replace(r"\\D", "", regex=True).str[-10:]
    return df.reset_index(drop=True)
''', reveals=["data cleaning", "pandas"])
add("survey analysis", "py", "survey.py", ["import pandas as pd"], '''
LIKERT = {"strongly disagree": 1, "disagree": 2, "neutral": 3, "agree": 4, "strongly agree": 5}


def score_items(df: pd.DataFrame, items: list[str]) -> pd.DataFrame:
    scored = df[items].apply(lambda col: col.str.lower().map(LIKERT))
    return scored.agg(["mean", "std", "count"]).T.round(2)


def crosstab(df, row, col):
    return pd.crosstab(df[row], df[col], normalize="index").round(3)
''', reveals=["survey analysis", "pandas"])
add("ETL", "py", "etl.py", ["import csv", "import psycopg"], '''
def extract(path):
    with open(path, newline="", encoding="utf-8") as fh:
        yield from csv.DictReader(fh)


def transform(rows):
    for r in rows:
        if not r.get("@ent@_id"):
            continue
        yield {
            "@ent@_id": r["@ent@_id"].strip(),
            "amount": round(float(r["amount"] or 0), 2),
            "day": r["date"][:10],
        }


def load(dsn, rows):
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO stg_@table@ (@ent@_id, amount, day) VALUES (%(@ent@_id)s, %(amount)s, %(day)s)", list(rows))
''', reveals=["ETL", "PostgreSQL"])
add("Mixpanel", "py", "export_events.py", ["import os", "import requests"], '''
EXPORT_URL = "https://data.mixpanel.com/api/2.0/export"


def export_events(from_date: str, to_date: str, event: str = "Signed Up"):
    resp = requests.get(
        EXPORT_URL,
        params={"from_date": from_date, "to_date": to_date, "event": f'["{event}"]'},
        auth=(os.environ["MIXPANEL_SECRET"], ""),
        timeout=120,
        stream=True,
    )
    resp.raise_for_status()
    for line in resp.iter_lines():
        if line:
            yield line.decode("utf-8")
''')
add("Excel", "py", "xlsx_report.py", ["from openpyxl import Workbook", "from openpyxl.styles import Font"], '''
def write_report(rows, path="monthly_summary.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    ws.append(["Region", "Revenue", "Target", "Gap %"])
    for r in rows:
        ws.append([r["region"], r["revenue"], r["target"], None])
    for i in range(2, len(rows) + 2):
        ws[f"D{i}"] = f"=(B{i}-C{i})/C{i}"
        ws[f"D{i}"].number_format = "0.0%"
    for cell in ws[1]:
        cell.font = Font(bold=True)
    wb.save(path)
''')
add("sales forecasting", "py", "projection.py", ["from statistics import mean"], '''
def project_quarter(monthly_revenue: list[float], growth_cap: float = 0.08):
    recent = monthly_revenue[-6:]
    growth = [b / a - 1 for a, b in zip(recent, recent[1:])]
    g = max(min(mean(growth), growth_cap), -growth_cap)
    base = monthly_revenue[-1]
    scenarios = {}
    for name, factor in {"low": 0.5, "base": 1.0, "high": 1.5}.items():
        scenarios[name] = [round(base * (1 + g * factor) ** m) for m in (1, 2, 3)]
    return scenarios
''')
add("data visualization", "py", "plots.py", ["import matplotlib.pyplot as plt"], '''
def trend_chart(months, values, title, path):
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(months, values, marker="o", linewidth=2)
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.annotate(f"{values[-1]:,.0f}", (months[-1], values[-1]), textcoords="offset points", xytext=(6, 6))
    fig.tight_layout()
    fig.savefig(path, dpi=160)
''')

# --------------------------------------------------------------- SQL / BI
add("SQL", "sql", "queries/weekly_summary.sql", [], '''
WITH weekly AS (
    SELECT
        date_trunc('week', created_at)          AS week,
        count(*)                                AS @table@,
        sum(amount)                             AS revenue,
        count(*) FILTER (WHERE status = 'refunded') AS refunds
    FROM @table@
    WHERE created_at >= current_date - interval '26 weeks'
    GROUP BY 1
)
SELECT
    week,
    @table@,
    revenue,
    round(refunds::numeric / nullif(@table@, 0), 4)           AS refund_rate,
    revenue - lag(revenue) OVER (ORDER BY week)               AS revenue_change,
    avg(revenue) OVER (ORDER BY week ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) AS revenue_4wk_avg
FROM weekly
ORDER BY week;
''')
add("dbt", "sql", "models/marts/fct_@table@.sql", [], '''
{{ config(materialized='incremental', unique_key='@ent@_id', on_schema_change='append_new_columns') }}

with source as (
    select * from {{ ref('stg_@table@') }}
    {% if is_incremental() %}
    where updated_at > (select max(updated_at) from {{ this }})
    {% endif %}
),

enriched as (
    select
        s.@ent@_id,
        s.customer_id,
        s.amount,
        s.status,
        c.segment,
        s.updated_at
    from source s
    left join {{ ref('dim_customers') }} c using (customer_id)
)

select * from enriched
''')
add("dbt", "yaml", "models/marts/schema.yml", [], '''
version: 2

models:
  - name: fct_@table@
    description: One row per @ent@, deduplicated and enriched with customer segment.
    columns:
      - name: @ent@_id
        tests: [unique, not_null]
      - name: customer_id
        tests:
          - not_null
          - relationships:
              to: ref('dim_customers')
              field: customer_id
      - name: status
        tests:
          - accepted_values:
              values: ['new', 'paid', 'refunded', 'cancelled']
''')
add("BigQuery", "sql", "bq/daily_events.sql", [], '''
-- partitioned by event_date, clustered by user_pseudo_id
CREATE OR REPLACE TABLE `analytics.daily_events`
PARTITION BY event_date
CLUSTER BY user_pseudo_id AS
SELECT
    PARSE_DATE('%Y%m%d', event_date)                      AS event_date,
    user_pseudo_id,
    event_name,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location') AS page,
    TIMESTAMP_MICROS(event_timestamp)                     AS event_ts
FROM `project.dataset.events_*`
WHERE _TABLE_SUFFIX BETWEEN '20240101' AND FORMAT_DATE('%Y%m%d', CURRENT_DATE());
''')
add("Google Analytics 4", "sql", "ga4/sessions.sql", [], '''
-- sessionise the GA4 export and attribute conversions to first-touch source
WITH sessions AS (
    SELECT
        user_pseudo_id,
        (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS session_id,
        MIN(TIMESTAMP_MICROS(event_timestamp))               AS session_start,
        ANY_VALUE(traffic_source.source)                     AS source,
        ANY_VALUE(traffic_source.medium)                     AS medium,
        COUNTIF(event_name = 'purchase')                     AS purchases
    FROM `project.analytics_123456.events_*`
    WHERE _TABLE_SUFFIX >= FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY))
    GROUP BY 1, 2
)
SELECT source, medium, COUNT(*) AS sessions, SUM(purchases) AS purchases,
       SAFE_DIVIDE(SUM(purchases), COUNT(*)) AS session_cr
FROM sessions
GROUP BY 1, 2
ORDER BY sessions DESC;
''', reveals=["Google Analytics 4", "BigQuery"])
add("Snowflake", "sql", "snowflake/usage.sql", [], '''
USE WAREHOUSE reporting_wh;

CREATE OR REPLACE VIEW analytics.warehouse_cost AS
SELECT
    date_trunc('day', start_time)       AS day,
    warehouse_name,
    sum(credits_used)                   AS credits,
    sum(credits_used) * 3.0             AS est_usd
FROM snowflake.account_usage.warehouse_metering_history
WHERE start_time >= dateadd('day', -90, current_timestamp())
GROUP BY 1, 2
QUALIFY row_number() OVER (PARTITION BY day ORDER BY credits DESC) <= 5;

ALTER WAREHOUSE reporting_wh SET AUTO_SUSPEND = 60 AUTO_RESUME = TRUE;
''')
add("funnel analysis", "sql", "funnel/checkout_funnel.sql", [], '''
WITH steps AS (
    SELECT
        user_id,
        min(CASE WHEN event = 'cart_view'    THEN ts END) AS t_cart,
        min(CASE WHEN event = 'address_done' THEN ts END) AS t_address,
        min(CASE WHEN event = 'payment_try'  THEN ts END) AS t_pay,
        min(CASE WHEN event = 'order_done'   THEN ts END) AS t_done
    FROM events
    WHERE ts >= current_date - 30
    GROUP BY user_id
)
SELECT
    count(t_cart)                                              AS cart,
    count(t_address)                                           AS address,
    count(t_pay)                                               AS payment,
    count(t_done)                                              AS done,
    round(100.0 * count(t_address) / nullif(count(t_cart), 0), 1) AS pct_to_address,
    round(100.0 * count(t_done) / nullif(count(t_pay), 0), 1)  AS pct_pay_success
FROM steps;
''')
add("data modeling", "sql", "warehouse/star_schema.sql", [], '''
CREATE TABLE dim_date (
    date_key     integer PRIMARY KEY,
    full_date    date NOT NULL,
    month_start  date NOT NULL,
    is_weekend   boolean NOT NULL
);

CREATE TABLE dim_customer (
    customer_key bigint PRIMARY KEY,
    customer_id  text NOT NULL,
    segment      text,
    valid_from   date NOT NULL,
    valid_to     date
);

CREATE TABLE fact_@table@ (
    @ent@_key     bigint PRIMARY KEY,
    date_key     integer REFERENCES dim_date (date_key),
    customer_key bigint  REFERENCES dim_customer (customer_key),
    amount       numeric(12, 2) NOT NULL,
    quantity     integer NOT NULL DEFAULT 1
);
''')
add("KPI definition", "sql", "metrics/kpi_views.sql", [], '''
-- metric dictionary: each KPI has one definition, owned by one team
CREATE OR REPLACE VIEW kpi_monthly AS
SELECT
    date_trunc('month', created_at)                                    AS month,
    sum(amount) FILTER (WHERE status = 'paid')                         AS net_revenue,
    count(DISTINCT customer_id) FILTER (WHERE status = 'paid')         AS paying_customers,
    sum(amount) FILTER (WHERE status = 'paid')
        / nullif(count(DISTINCT customer_id) FILTER (WHERE status = 'paid'), 0) AS arpu,
    count(*) FILTER (WHERE status = 'refunded')::numeric / nullif(count(*), 0)  AS refund_rate
FROM @table@
GROUP BY 1;

COMMENT ON VIEW kpi_monthly IS 'Owner: finance. Refunds counted in the month of the original sale.';
''')
add("DAX", "dax", "measures.dax", [], '''
Total Sales = SUM ( Sales[Amount] )

Sales LY = CALCULATE ( [Total Sales], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )

Sales YoY % = DIVIDE ( [Total Sales] - [Sales LY], [Sales LY] )

Sales 3M Avg =
AVERAGEX (
    DATESINPERIOD ( 'Date'[Date], MAX ( 'Date'[Date] ), -3, MONTH ),
    [Total Sales]
)

Return Rate =
DIVIDE (
    CALCULATE ( COUNTROWS ( Sales ), Sales[Status] = "Returned" ),
    COUNTROWS ( Sales )
)
''', reveals=["DAX", "Power BI"])
add("Looker", "lkml", "views/@table@.view.lkml", [], '''
view: @table@ {
  sql_table_name: analytics.fct_@table@ ;;

  dimension: @ent@_id {
    primary_key: yes
    type: string
    sql: ${TABLE}.@ent@_id ;;
  }

  dimension_group: created {
    type: time
    timeframes: [date, week, month, quarter]
    sql: ${TABLE}.created_at ;;
  }

  measure: total_amount {
    type: sum
    sql: ${TABLE}.amount ;;
    value_format_name: usd
  }

  measure: count_@table@ {
    type: count_distinct
    sql: ${@ent@_id} ;;
  }
}
''')
add("Google Apps Script", "js", "Code.gs", [], '''
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Reports')
    .addItem('Refresh weekly summary', 'refreshSummary')
    .addToUi();
}

function refreshSummary() {
  const ss = SpreadsheetApp.getActive();
  const raw = ss.getSheetByName('Raw').getDataRange().getValues();
  const [header, ...rows] = raw;
  const totals = {};
  rows.forEach(r => { totals[r[1]] = (totals[r[1]] || 0) + Number(r[3] || 0); });
  const out = Object.entries(totals).map(([k, v]) => [k, v]);
  ss.getSheetByName('Summary').getRange(2, 1, out.length, 2).setValues(out);
  MailApp.sendEmail('ops@example.org', 'Weekly summary refreshed', 'Rows processed: ' + rows.length);
}
''')

# ------------------------------------------------------- typescript / js
add("React", "tsx", "src/components/@Ent@List.tsx", ["import { useEffect, useState } from 'react';"], '''
export function @Ent@List({ status }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/@table@?status=${status}`)
      .then((r) => r.json())
      .then((data) => { if (!cancelled) { setItems(data); setLoading(false); } });
    return () => { cancelled = true; };
  }, [status]);

  if (loading) return <p>Loading...</p>;
  return (
    <ul>
      {items.map((it) => (
        <li key={it.id}>{it.reference} - {it.status}</li>
      ))}
    </ul>
  );
}
''')
add("Next.js", "tsx", "app/api/@table@/route.ts", ["import { NextResponse } from 'next/server';"], '''
export async function GET(req) {
  const { searchParams } = new URL(req.url);
  const page = Number(searchParams.get('page') ?? '1');
  const rows = await listPage(page, 20);
  return NextResponse.json({ page, rows }, { headers: { 'Cache-Control': 's-maxage=30, stale-while-revalidate=120' } });
}

export async function POST(req) {
  const body = await req.json();
  if (!body.name) {
    return NextResponse.json({ error: 'name is required' }, { status: 400 });
  }
  const created = await create@Ent@(body);
  return NextResponse.json(created, { status: 201 });
}

export const revalidate = 60;
''')
add("TypeScript", "ts", "src/types.ts", [], '''
export type @Ent@Status = 'new' | 'paid' | 'cancelled';

export interface @Ent@ {
  id: string;
  reference: string;
  status: @Ent@Status;
  totalCents: number;
  createdAt: string;
}

export interface Page<T> {
  items: T[];
  nextCursor: string | null;
}

export function isPaid(x: @Ent@): boolean {
  return x.status === 'paid' && x.totalCents > 0;
}

export function groupByStatus(items: @Ent@[]): Record<@Ent@Status, @Ent@[]> {
  const out: Record<@Ent@Status, @Ent@[]> = { new: [], paid: [], cancelled: [] };
  for (const it of items) out[it.status].push(it);
  return out;
}
''')
add("Node.js", "ts", "src/server.ts", ["import http from 'node:http';"], '''
const server = http.createServer(async (req, res) => {
  if (req.url === '/healthz') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify({ ok: true, uptime: process.uptime() }));
  }
  res.writeHead(404);
  res.end();
});

const port = Number(process.env.PORT ?? 3000);
server.listen(port, () => console.log(`listening on ${port}`));

process.on('SIGTERM', () => {
  server.close(() => process.exit(0));
});
''')
add("Express", "ts", "src/routes/@table@.ts", ["import { Router } from 'express';"], '''
export const router = Router();

router.get('/', async (req, res, next) => {
  try {
    const limit = Math.min(Number(req.query.limit ?? 20), 100);
    const rows = await db.list@Ent@(req.query.cursor, limit);
    res.json({ items: rows, nextCursor: rows.length === limit ? rows[rows.length - 1].id : null });
  } catch (err) {
    next(err);
  }
});

router.post('/', validateBody(create@Ent@Schema), async (req, res, next) => {
  try {
    res.status(201).json(await db.create@Ent@(req.body));
  } catch (err) {
    next(err);
  }
});
''')
add("NestJS", "ts", "src/@table@/@table@.controller.ts", ["import { Body, Controller, Get, Param, Post, UseGuards } from '@nestjs/common';"], '''
@Controller('@table@')
@UseGuards(AuthGuard)
export class @Ent@Controller {
  constructor(private readonly service: @Ent@Service) {}

  @Get()
  findAll() {
    return this.service.findAll();
  }

  @Get(':id')
  findOne(@Param('id') id: string) {
    return this.service.findOne(id);
  }

  @Post()
  create(@Body() dto: Create@Ent@Dto) {
    return this.service.create(dto);
  }
}
''')
add("Prisma", "prisma", "prisma/schema.prisma", [], '''
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model @Ent@ {
  id        String   @id @default(cuid())
  reference String   @unique
  status    String   @default("new")
  total     Int      @default(0)
  owner     User     @relation(fields: [ownerId], references: [id])
  ownerId   String
  createdAt DateTime @default(now())

  @@index([ownerId, status])
}

model User {
  id    String @id @default(cuid())
  email String @unique
  @table@ @Ent@[]
}
''')
add("MongoDB", "ts", "src/models/@ent@.ts", ["import mongoose from 'mongoose';"], '''
const @ent@Schema = new mongoose.Schema(
  {
    title: { type: String, required: true, trim: true },
    body: { type: String, default: '' },
    status: { type: String, enum: ['draft', 'scheduled', 'published'], default: 'draft', index: true },
    publishAt: { type: Date },
    tags: [{ type: String, index: true }],
  },
  { timestamps: true }
);

@ent@Schema.index({ status: 1, publishAt: 1 });

export const @Ent@Model = mongoose.model('@Ent@', @ent@Schema);

export async function dueToPublish(now = new Date()) {
  return @Ent@Model.find({ status: 'scheduled', publishAt: { $lte: now } }).limit(100);
}
''')
add("GraphQL", "ts", "src/schema.ts", ["import { gql } from 'graphql-tag';"], '''
export const typeDefs = gql`
  type @Ent@ {
    id: ID!
    reference: String!
    status: String!
    totalCents: Int!
  }

  type Query {
    @ent@(id: ID!): @Ent@
    @table@(status: String, first: Int = 20, after: String): [@Ent@!]!
  }

  type Mutation {
    cancel@Ent@(id: ID!): @Ent@!
  }
`;

export const resolvers = {
  Query: {
    @ent@: (_p, { id }, ctx) => ctx.loaders.@ent@.load(id),
    @table@: (_p, args, ctx) => ctx.db.list@Ent@(args),
  },
};
''')
add("REST API design", "yaml", "openapi.yaml", [], '''
openapi: 3.0.3
info:
  title: @Ent@ API
  version: 2.1.0
paths:
  /v2/@table@:
    get:
      summary: List @table@
      parameters:
        - { name: limit, in: query, schema: { type: integer, default: 20, maximum: 100 } }
        - { name: cursor, in: query, schema: { type: string } }
      responses:
        "200": { description: A page of @table@ }
    post:
      summary: Create an @ent@
      parameters:
        - { name: Idempotency-Key, in: header, required: true, schema: { type: string } }
      responses:
        "201": { description: Created }
        "409": { description: Duplicate idempotency key with different payload }
''')
add("Stripe", "ts", "src/billing/webhook.ts", ["import Stripe from 'stripe';"], '''
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY, { apiVersion: '2023-10-16' });

export async function createCheckout(customerId, priceId) {
  return stripe.checkout.sessions.create({
    mode: 'subscription',
    customer: customerId,
    line_items: [{ price: priceId, quantity: 1 }],
    success_url: `${process.env.APP_URL}/billing?ok=1`,
    cancel_url: `${process.env.APP_URL}/billing`,
  });
}

export function handleWebhook(rawBody, signature) {
  const event = stripe.webhooks.constructEvent(rawBody, signature, process.env.STRIPE_WEBHOOK_SECRET);
  switch (event.type) {
    case 'invoice.payment_failed':
      return flagPastDue(event.data.object.customer);
    case 'checkout.session.completed':
      return activate(event.data.object);
    default:
      return null;
  }
}
''')
add("Tailwind CSS", "tsx", "src/components/Card.tsx", [], '''
export function Card({ title, children }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm hover:shadow-md transition-shadow dark:border-slate-700 dark:bg-slate-900">
      <h3 className="mb-2 text-lg font-semibold tracking-tight text-slate-900 dark:text-slate-100">{title}</h3>
      <div className="space-y-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{children}</div>
    </section>
  );
}
''')
add("Tailwind CSS", "js", "tailwind.config.js", [], '''
module.exports = {
  content: ['./app/**/*.{ts,tsx}', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: { brand: { 50: '#eef6ff', 500: '#2563eb', 700: '#1d4ed8' } },
      fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] },
    },
  },
  plugins: [require('@tailwindcss/forms')],
};
''')
add("WebSockets", "ts", "src/realtime.ts", ["import { WebSocketServer } from 'ws';"], '''
const wss = new WebSocketServer({ port: 8081 });
const rooms = new Map();

wss.on('connection', (socket, req) => {
  const room = new URL(req.url, 'http://x').searchParams.get('room') ?? 'lobby';
  if (!rooms.has(room)) rooms.set(room, new Set());
  rooms.get(room).add(socket);

  socket.on('message', (raw) => {
    for (const peer of rooms.get(room)) {
      if (peer !== socket && peer.readyState === 1) peer.send(raw.toString());
    }
  });

  socket.on('close', () => rooms.get(room).delete(socket));
});

setInterval(() => wss.clients.forEach((c) => c.ping()), 30000);
''')
add("OAuth", "ts", "src/auth/oidc.ts", ["import { auth } from 'express-openid-connect';"], '''
export const oidc = auth({
  issuerBaseURL: process.env.AUTH0_ISSUER,
  baseURL: process.env.APP_URL,
  clientID: process.env.AUTH0_CLIENT_ID,
  secret: process.env.SESSION_SECRET,
  authRequired: false,
  authorizationParams: { response_type: 'code', scope: 'openid profile email offline_access' },
  afterCallback: async (req, res, session) => {
    await upsertUserFromClaims(session.id_token);
    return session;
  },
});
''')
add("JWT authentication", "ts", "src/auth/jwt.ts", ["import jwt from 'jsonwebtoken';"], '''
const ACCESS_TTL = '15m';

export function signAccess(userId, role) {
  return jwt.sign({ sub: userId, role }, process.env.JWT_SECRET, { expiresIn: ACCESS_TTL });
}

export function requireAuth(req, res, next) {
  const header = req.headers.authorization ?? '';
  const token = header.startsWith('Bearer ') ? header.slice(7) : null;
  if (!token) return res.status(401).json({ error: 'missing token' });
  try {
    req.user = jwt.verify(token, process.env.JWT_SECRET);
    return next();
  } catch {
    return res.status(401).json({ error: 'invalid or expired token' });
  }
}
''')
add("Playwright", "ts", "tests/e2e/checkout.spec.ts", ["import { expect, test } from '@playwright/test';"], '''
test.describe('checkout', () => {
  test('guest can buy a single item', async ({ page }) => {
    await page.goto('/products/ceramic-mug');
    await page.getByRole('button', { name: 'Add to cart' }).click();
    await page.getByRole('link', { name: 'Checkout' }).click();
    await page.getByLabel('Email').fill('guest@example.com');
    await page.getByRole('button', { name: 'Pay now' }).click();
    await expect(page.getByText('Order confirmed')).toBeVisible();
  });

  test('shows an error for a declined card', async ({ page }) => {
    await page.goto('/checkout?test_card=declined');
    await page.getByRole('button', { name: 'Pay now' }).click();
    await expect(page.getByRole('alert')).toContainText('declined');
  });
});
''')
add("Cypress", "js", "cypress/e2e/checkout.cy.js", [], '''
describe('checkout flow', () => {
  beforeEach(() => {
    cy.intercept('POST', '/api/payments', { statusCode: 200, body: { ok: true } }).as('pay');
    cy.visit('/cart');
  });

  it('completes an order with a saved card', () => {
    cy.get('[data-test=checkout]').click();
    cy.get('[data-test=card-saved]').first().click();
    cy.get('[data-test=pay]').click();
    cy.wait('@pay');
    cy.contains('Thank you for your order').should('be.visible');
  });

  it('blocks submit when the address is incomplete', () => {
    cy.get('[data-test=checkout]').click();
    cy.get('[data-test=pay]').click();
    cy.contains('Address is required').should('be.visible');
  });
});
''')
add("Jest", "ts", "src/__tests__/totals.test.ts", [], '''
import { calculateTotal } from '../totals';

describe('calculateTotal', () => {
  it('sums line items and applies a percentage discount', () => {
    const total = calculateTotal([{ cents: 1000, qty: 2 }, { cents: 550, qty: 1 }], { percent: 10 });
    expect(total).toBe(2295);
  });

  it('never returns a negative total', () => {
    expect(calculateTotal([{ cents: 100, qty: 1 }], { percent: 150 })).toBe(0);
  });

  it('throws on a negative quantity', () => {
    expect(() => calculateTotal([{ cents: 100, qty: -1 }], null)).toThrow('quantity');
  });
});
''')
add("Redis", "ts", "src/cache.ts", ["import Redis from 'ioredis';"], '''
const redis = new Redis(process.env.REDIS_URL ?? 'redis://localhost:6379');

export async function cached(key, ttlSeconds, loader) {
  const hit = await redis.get(key);
  if (hit) return JSON.parse(hit);
  const fresh = await loader();
  await redis.set(key, JSON.stringify(fresh), 'EX', ttlSeconds);
  return fresh;
}

export async function rateLimit(ip, limit = 100) {
  const k = `rl:${ip}`;
  const n = await redis.incr(k);
  if (n === 1) await redis.expire(k, 60);
  return n <= limit;
}
''')
add("PostgreSQL", "sql", "db/migrations/0004_add_indexes.sql", [], '''
BEGIN;

ALTER TABLE @table@ ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX CONCURRENTLY IF NOT EXISTS @table@_status_created_idx
    ON @table@ (status, created_at DESC)
    WHERE status <> 'archived';

CREATE INDEX IF NOT EXISTS @table@_metadata_gin ON @table@ USING gin (metadata jsonb_path_ops);

ALTER TABLE @table@
    ADD CONSTRAINT @table@_total_nonneg CHECK (total_cents >= 0);

COMMIT;
''')
add("AWS", "ts", "infra/upload.ts", ["import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';",
                                      "import { getSignedUrl } from '@aws-sdk/s3-request-presigner';"], '''
const s3 = new S3Client({ region: 'eu-west-1' });

export async function presignUpload(key, contentType) {
  const cmd = new PutObjectCommand({ Bucket: process.env.UPLOAD_BUCKET, Key: key, ContentType: contentType });
  return getSignedUrl(s3, cmd, { expiresIn: 900 });
}
''')
add("Vercel", "json", "vercel.json", [], '''
{
  "framework": "nextjs",
  "regions": ["fra1"],
  "buildCommand": "npm run build",
  "installCommand": "npm ci",
  "crons": [
    { "path": "/api/cron/reindex", "schedule": "0 3 * * *" },
    { "path": "/api/cron/expire-holds", "schedule": "*/15 * * * *" }
  ],
  "functions": {
    "app/api/**/*.ts": { "maxDuration": 30, "memory": 1024 }
  },
  "headers": [
    {
      "source": "/api/(.*)",
      "headers": [
        { "key": "Cache-Control", "value": "s-maxage=30, stale-while-revalidate=120" },
        { "key": "X-Content-Type-Options", "value": "nosniff" }
      ]
    },
    {
      "source": "/(.*)",
      "headers": [{ "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" }]
    }
  ],
  "redirects": [
    { "source": "/old-listings/:id", "destination": "/listings/:id", "permanent": true },
    { "source": "/search/:q", "destination": "/listings?q=:q", "permanent": false }
  ],
  "rewrites": [{ "source": "/sitemap.xml", "destination": "/api/sitemap" }]
}
''')
add("Shopify", "liquid", "sections/featured-collection.liquid", [], '''
<section class="featured" data-section-id="{{ section.id }}">
  <h2>{{ section.settings.heading | default: collection.title }}</h2>
  <ul class="grid">
    {%- for product in collections[section.settings.collection].products limit: section.settings.limit -%}
      <li class="card">
        <a href="{{ product.url }}">
          {{ product.featured_image | image_url: width: 600 | image_tag: loading: 'lazy' }}
          <span class="title">{{ product.title }}</span>
          <span class="price">{{ product.price | money }}</span>
        </a>
      </li>
    {%- endfor -%}
  </ul>
</section>

{% schema %}
{ "name": "Featured collection",
  "settings": [
    { "type": "collection", "id": "collection", "label": "Collection" },
    { "type": "range", "id": "limit", "min": 2, "max": 12, "step": 1, "default": 4, "label": "Products" }
  ] }
{% endschema %}
''')
add("JavaScript", "js", "assets/cart-drawer.js", [], '''
class CartDrawer extends HTMLElement {
  connectedCallback() {
    this.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-remove]');
      if (btn) this.update(btn.dataset.remove, 0);
    });
  }

  async update(line, quantity) {
    const res = await fetch('/cart/change.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ line, quantity }),
    });
    const cart = await res.json();
    document.querySelector('[data-cart-count]').textContent = cart.item_count;
    this.render(cart);
  }

  render(cart) { this.querySelector('[data-total]').textContent = (cart.total_price / 100).toFixed(2); }
}
customElements.define('cart-drawer', CartDrawer);
''')
add("Redux", "ts", "src/store/@table@Slice.ts", ["import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';"], '''
export const fetch@Ent@ = createAsyncThunk('@table@/fetch', async (id) => {
  const res = await fetch(`/api/@table@/${id}`);
  return res.json();
});

const slice = createSlice({
  name: '@table@',
  initialState: { byId: {}, status: 'idle' },
  reducers: {
    upsert(state, action) {
      state.byId[action.payload.id] = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetch@Ent@.pending, (s) => { s.status = 'loading'; })
      .addCase(fetch@Ent@.fulfilled, (s, a) => { s.status = 'idle'; s.byId[a.payload.id] = a.payload; });
  },
});

export const { upsert } = slice.actions;
export default slice.reducer;
''')
add("GitHub Actions", "yaml", ".github/workflows/ci.yml", [], '''
name: ci
on:
  pull_request:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      db:
        image: postgres:16
        env: { POSTGRES_PASSWORD: test }
        ports: ["5432:5432"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm }
      - run: npm ci
      - run: npm test -- --coverage
      - run: npx playwright install --with-deps chromium
      - run: npx playwright test
  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - run: echo "deploying"
''')
add("HTML/CSS", "css", "styles/layout.css", [], '''
:root {
  --gap: clamp(12px, 2vw, 24px);
  --max: 1120px;
}

.container {
  width: min(100% - 2 * var(--gap), var(--max));
  margin-inline: auto;
}

.grid {
  display: grid;
  gap: var(--gap);
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
}

.nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

@media (max-width: 640px) {
  .nav { flex-direction: column; gap: 8px; }
  .hero h1 { font-size: 1.75rem; }
}
''')
add("Elasticsearch", "ts", "src/search.ts", ["import { Client } from '@elastic/elasticsearch';"], '''
const es = new Client({ node: process.env.ES_URL });

export async function searchListings(q, filters = {}) {
  const res = await es.search({
    index: 'listings',
    size: 24,
    query: {
      bool: {
        must: q ? [{ multi_match: { query: q, fields: ['title^3', 'description'], fuzziness: 'AUTO' } }] : [],
        filter: [
          ...(filters.maxPrice ? [{ range: { price: { lte: filters.maxPrice } } }] : []),
          ...(filters.bbox ? [{ geo_bounding_box: { location: filters.bbox } }] : []),
        ],
      },
    },
    aggs: { beds: { terms: { field: 'bedrooms' } } },
  });
  return res.hits.hits.map((h) => ({ id: h._id, ...h._source }));
}
''')
add("Firebase", "ts", "src/firebase.ts", ["import { initializeApp } from 'firebase/app';",
                                          "import { collection, doc, getFirestore, onSnapshot } from 'firebase/firestore';"], '''
const app = initializeApp({ apiKey: process.env.FIREBASE_KEY, projectId: 'trip-planner-prod' });
export const db = getFirestore(app);

export function watchTrip(tripId, onChange) {
  return onSnapshot(collection(db, 'trips', tripId, 'stops'), (snap) => {
    onChange(snap.docs.map((d) => ({ id: d.id, ...d.data() })));
  });
}

export const stopRef = (tripId, stopId) => doc(db, 'trips', tripId, 'stops', stopId);
''')
add("RabbitMQ", "ts", "src/queue.ts", ["import amqp from 'amqplib';"], '''
const QUEUE = 'stock-alerts';

export async function publishAlert(payload) {
  const conn = await amqp.connect(process.env.AMQP_URL);
  const ch = await conn.createChannel();
  await ch.assertQueue(QUEUE, { durable: true });
  ch.sendToQueue(QUEUE, Buffer.from(JSON.stringify(payload)), { persistent: true });
  await ch.close();
  await conn.close();
}

export async function consume(handler) {
  const conn = await amqp.connect(process.env.AMQP_URL);
  const ch = await conn.createChannel();
  await ch.assertQueue(QUEUE, { durable: true });
  ch.prefetch(10);
  ch.consume(QUEUE, async (msg) => {
    if (!msg) return;
    try { await handler(JSON.parse(msg.content.toString())); ch.ack(msg); } catch { ch.nack(msg, false, false); }
  });
}
''')
add("Bash scripting", "sh", "scripts/deploy.sh", [], '''
#!/usr/bin/env bash
set -euo pipefail

APP=${1:?usage: deploy.sh <app> [tag]}
TAG=${2:-$(git rev-parse --short HEAD)}

echo "building $APP:$TAG"
docker build -t "registry.example.com/$APP:$TAG" .
docker push "registry.example.com/$APP:$TAG"

ssh deploy@app-host "docker pull registry.example.com/$APP:$TAG && \\
  docker compose -f /srv/$APP/compose.yml up -d --no-deps $APP"

for i in 1 2 3 4 5; do
  if curl -sf "https://$APP.example.com/healthz" > /dev/null; then echo ok; exit 0; fi
  sleep 3
done
echo "health check failed, rolling back" >&2
exit 1
''')

# helper structure ----------------------------------------------------------------------------
BASE_LANG_SKILLS = {"Python", "SQL", "TypeScript", "JavaScript"}
LANG_OF_EXT = {"py": "Python", "sql": "SQL", "ts": "TypeScript", "tsx": "TypeScript", "js": "JavaScript"}

FILLER_PY = [
    ('import logging', '''
logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
'''),
    ('from pathlib import Path\nimport json', '''
def load_config(path: str = "config.json") -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))
'''),
    ('', '''
def chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]
'''),
    ('import time', '''
def retry(fn, attempts=3, delay=1.0):
    for n in range(attempts):
        try:
            return fn()
        except Exception:
            if n == attempts - 1:
                raise
            time.sleep(delay * (2 ** n))
'''),
]
FILLER_TS = [
    '''
export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
''',
    '''
export function required(name) {
  const v = process.env[name];
  if (!v) throw new Error(`missing env var ${name}`);
  return v;
}
''',
    '''
export function paginate(items, page = 1, size = 20) {
  const start = (page - 1) * size;
  return { items: items.slice(start, start + size), total: items.length, page, size };
}
''',
]
PAD_NOTES = [
    "Kept deliberately small: one file per concern, no framework magic.",
    "TODO: move the hard-coded values below into environment config.",
    "Known limitation: assumes UTC timestamps everywhere.",
    "Run the tests before changing anything in this file.",
    "Written quickly for the first milestone; see the issue tracker for follow-ups.",
    "Naming follows the client's glossary, not ours.",
    "Do not commit real credentials; use the .env.example as a template.",
    "Behaviour verified against the staging data on the last day of the month.",
    "Edge case: empty input returns early instead of raising.",
    "Owner on the client side: the operations lead. Ask before changing defaults.",
    "Deployed from the main branch only; feature branches are not built.",
    "Temporary workaround kept until the upstream export format is fixed.",
    "Reviewed with the client's developer during the handover week.",
    "Performance was measured on a copy of last quarter's data.",
    "Retention of old records is handled elsewhere (see the runbook).",
    "The numbers here were agreed in the kickoff workshop and written down.",
    "If this breaks at month end, check the date handling first.",
    "Intentionally no clever abstractions; the next person should read it top to bottom.",
    "Secrets are injected at deploy time and never logged.",
    "Added after the second review round; keep in sync with the docs.",
    "Rate limits on the upstream service are generous but not infinite.",
    "Sample values are fictional.",
    "Last touched during the final week of the engagement.",
    "Anything marked legacy can be deleted once phase two ships.",
    "Formatting follows the team's default linter settings.",
    "Check the changelog before upgrading dependencies.",
    "This module has no side effects on import.",
    "Logging is intentionally terse; verbose mode lives in the config.",
]
