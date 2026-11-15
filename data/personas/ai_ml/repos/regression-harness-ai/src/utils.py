"""Regression harness for an AI drafting tool: utils helpers."""

import json
import statistics

from openai import OpenAI


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


RUBRIC = "Score 1-5 for factual accuracy, 1-5 for completeness. Reply as JSON: {\"acc\": n, \"comp\": n}."


def judge(call_model, question, reference, answer):
    reply = call_model(f"{RUBRIC}\nQ: {question}\nReference: {reference}\nAnswer: {answer}")
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
