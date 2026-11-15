"""CI rule: every number in the README results tables traces to evals/results/.
Numbers inside <!-- results:start --> ... <!-- results:end --> blocks are checked against
every number found in evals/results/*.json (rounded to the precision the README shows,
also accepting the value x100 for percentages)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def numbers_in(obj, out: set[float]) -> None:
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        out.add(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            numbers_in(v, out)
    elif isinstance(obj, list):
        for v in obj:
            numbers_in(v, out)


def main() -> int:
    vals: set[float] = set()
    for p in (ROOT / "evals" / "results").glob("*.json"):
        numbers_in(json.loads(p.read_text(encoding="utf-8")), vals)
    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
    blocks = re.findall(r"<!-- results:start -->(.*?)<!-- results:end -->", readme, re.S)
    missing = []
    for block in blocks:
        for tok in re.findall(r"(?<![\w.$-])\d+\.\d+(?![\w.])", block):
            places = len(tok.split(".")[1])
            cands = {round(v, places) for v in vals} | {round(v * 100, places) for v in vals}
            if round(float(tok), places) not in cands:
                missing.append(tok)
    if missing:
        print("numbers in README results blocks not found in evals/results:", sorted(set(missing)))
        return 1
    print(f"numbers OK ({len(blocks)} results blocks checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
