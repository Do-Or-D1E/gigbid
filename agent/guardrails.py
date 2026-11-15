"""Guardrails used across the system.

* untrusted(): wraps third-party text in data tags and neutralises tag look-alikes so a
  job post cannot close the tag and talk as the system.
* detect_injection(): cheap pattern screen that runs before any model sees the text. Hits
  are recorded and passed to the Risk Assessor; the text is still analysed, never obeyed.
* mask_pii(): masks emails, phone numbers, messaging handles and card/IBAN numbers in
  logs, traces and the audit log.
* contact_details(): finds contact details inside drafts (Compliance Guard pre-check)."""
from __future__ import annotations

import re
from typing import Any

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
_HANDLE = re.compile(r"(?i)\b(?:telegram|whats\s?app|wa\.me|signal|skype|discord|wechat)\b[\s:@/.-]*@?[\w.+-]{3,}")
_CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
_URL = re.compile(r"https?://[^\s)>\]]+|www\.[^\s)>\]]+", re.I)

INJECTION_PATTERNS = [
    r"ignore (?:all |any |the )?(?:previous|prior|above|earlier) (?:instructions|rules|prompts?)",
    r"disregard (?:all |your |the )?(?:previous|prior|above) ",
    r"(?:note|message|instructions?) (?:to|for) (?:ai|llm|chatgpt|gpt|assistants?|language models?|bots?)",
    r"if you are an? (?:ai|language model|llm|assistant|bot)",
    r"\[\s*system[^\]]*\]|<\s*/?\s*system\s*>|system override",
    r"(?:print|reveal|show|output|repeat) (?:your |the )?(?:full |entire )?(?:system )?prompt",
    r"(?:begin|start) (?:the|your) (?:proposal|reply|response) with (?:the )?(?:exact )?(?:phrase|words?)",
    r"(?:rate|score|mark) this (?:job|post)",
    r"recommend (?:bidding|to bid) regardless",
    r"set (?:the |your )?(?:price|bid|rate) to",
    r"already approved a bid",
    r"(?:include|put|add|share) your (?:personal )?(?:email|phone|whatsapp|telegram|number|contact)",
]
_INJ = [re.compile(p, re.I) for p in INJECTION_PATTERNS]


def defences_on() -> bool:
    import os

    return os.environ.get("GIGBID_DEFENCES", "on") != "off"


def untrusted(tag: str, text: str) -> str:
    if not defences_on():
        return text or ""
    safe = re.sub(r"<\s*/?\s*(job_post|client_message|client_history|evidence|system)[^>]*>", "[tag removed]",
                  text or "", flags=re.I)
    return f"<{tag}>\n{safe}\n</{tag}>"


def detect_injection(text: str) -> list[str]:
    if not defences_on():
        return []
    hits = []
    for pat in _INJ:
        for m in pat.finditer(text or ""):
            start = max(0, m.start() - 60)
            hits.append((text[start:m.end() + 80]).strip())
    return list(dict.fromkeys(hits))


def mask_pii(value: Any) -> Any:
    if isinstance(value, str):
        v = _EMAIL.sub("[email]", value)
        v = _HANDLE.sub("[handle]", v)
        v = _IBAN.sub("[iban]", v)
        v = _CARD.sub(lambda m: "[card]" if len(re.sub(r"\D", "", m.group(0))) >= 13 else m.group(0), v)
        v = _PHONE.sub(lambda m: "[phone]" if len(re.sub(r"\D", "", m.group(0))) >= 9 else m.group(0), v)
        return v
    if isinstance(value, dict):
        return {k: ("[redacted]" if any(s in k.lower() for s in ("token", "secret", "password", "authorization"))
                    else mask_pii(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [mask_pii(v) for v in value]
    return value


def contact_details(text: str) -> list[str]:
    found = _EMAIL.findall(text) + [m.group(0) for m in _HANDLE.finditer(text)]
    found += [m.group(0) for m in _PHONE.finditer(text) if len(re.sub(r"\D", "", m.group(0))) >= 9]
    return list(dict.fromkeys(found))


def urls(text: str) -> list[str]:
    return _URL.findall(text or "")


GUARANTEE = re.compile(r"\b(guarantee[ds]?|100\s?%|promise (?:you )?(?:results|success)|risk[- ]free|"
                       r"money[- ]back)\b", re.I)


def guarantees(text: str) -> list[str]:
    return [m.group(0) for m in GUARANTEE.finditer(text or "")]
