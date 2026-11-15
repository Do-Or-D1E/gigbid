from collections import defaultdict
import json
import math

from openai import OpenAI


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
    cited = "\n".join(f"[{i + 1}] {t}" for i, (_, _, t) in enumerate(hits))
    return f"Answer from the numbered passages only and cite them.\n{cited}\n\nQ: {question}"


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
