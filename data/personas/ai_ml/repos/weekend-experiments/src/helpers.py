"""Invoice field extraction for accounts payable: helpers helpers."""

import re

from PIL import Image, ImageOps
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pytesseract
import spacy


nlp = spacy.load("en_core_web_trf", disable=["lemmatizer"])
KEEP = {"ORG", "PERSON", "GPE", "MONEY", "DATE"}


def extract_entities(text: str) -> dict[str, list[str]]:
    doc = nlp(text)
    found: dict[str, list[str]] = {}
    for ent in doc.ents:
        if ent.label_ in KEEP:
            found.setdefault(ent.label_, []).append(ent.text.strip())
    return {k: sorted(set(v)) for k, v in found.items()}


AMOUNT = re.compile(r"(?:total|amount due)[^0-9]{0,12}([0-9][0-9,]*\.[0-9]{2})", re.I)


def read_page(path: str) -> str:
    img = ImageOps.autocontrast(Image.open(path).convert("L"))
    return pytesseract.image_to_string(img, config="--psm 6")


def find_total(text: str):
    m = AMOUNT.search(text)
    return float(m.group(1).replace(",", "")) if m else None


app = FastAPI(title="Transaction service", version="1.3.0")


class ScoreRequest(BaseModel):
    transaction_id: str
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
