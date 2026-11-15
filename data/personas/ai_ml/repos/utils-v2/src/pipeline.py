"""Contract question-answering assistant: pipeline helpers."""

import json

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from openai import OpenAI


prompt = ChatPromptTemplate.from_messages([
    ("system", "You answer using only the context. If the context is not enough, say so."),
    ("human", "Context:\n{context}\n\nQuestion: {question}"),
])
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
chain = prompt | llm | StrOutputParser()


def answer(question: str, docs: list[str]) -> str:
    return chain.invoke({"context": "\n---\n".join(docs), "question": question})


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
