"""Small shared helpers for the GigBid data generator (stdlib only, deterministic)."""
from __future__ import annotations

import datetime as _dt
import json
import re
from pathlib import Path


def dumps(obj, indent: int | None = 2) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, indent=indent)


def write_text(path, text: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def write_json(path, obj, indent: int | None = 2) -> None:
    write_text(path, dumps(obj, indent=indent))


def write_jsonl(path, rows) -> None:
    write_text(path, "\n".join(json.dumps(r, sort_keys=True, ensure_ascii=True) for r in rows))


def cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def pick(rng, seq):
    return seq[rng.randrange(len(seq))]


def pick_n(rng, seq, n):
    seq = list(seq)
    n = min(n, len(seq))
    return rng.sample(seq, n)


def chance(rng, p: float) -> bool:
    return rng.random() < p


def weighted(rng, pairs):
    """pairs: [(value, weight), ...]"""
    total = sum(w for _, w in pairs)
    r = rng.random() * total
    acc = 0.0
    for v, w in pairs:
        acc += w
        if r <= acc:
            return v
    return pairs[-1][0]


def nwords(text: str) -> int:
    return len(text.split())


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def a_an(label: str) -> str:
    l = label.lower()
    return ("an " if l[0] in "aeiou" or l.startswith(("e-", "hr")) else "a ") + label


def has_term(text: str, term: str) -> bool:
    """Case-insensitive whole-term match (alphanumeric boundaries)."""
    pat = r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])"
    return re.search(pat, text, flags=re.IGNORECASE) is not None


def rand_date(rng, start: _dt.date, end: _dt.date) -> _dt.date:
    span = (end - start).days
    return start + _dt.timedelta(days=rng.randrange(span + 1))


def iso_dt(d: _dt.date, hour: int, minute: int) -> str:
    return f"{d.isoformat()}T{hour:02d}:{minute:02d}:00Z"


def month_str(d: _dt.date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def join_and(items, conj="and"):
    items = list(items)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} {conj} {items[1]}"
    return ", ".join(items[:-1]) + f", {conj} " + items[-1]


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
