"""CI rule: every prompt lives in agent/prompts/. Fails if any llm.call passes a literal
system prompt instead of load_prompt(...), or a node builds an inline SystemMessage."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    bad = []
    for path in list((ROOT / "agent").rglob("*.py")) + list((ROOT / "rag").rglob("*.py")):
        if "prompts" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"llm\.call\(\s*\"[^\"]+\",\s*([^,]+),", text):
            if m.group(1).strip().startswith(("\"", "'", "f\"", "f'")):
                bad.append(f"{path.relative_to(ROOT)}: literal system prompt in llm.call")
        if re.search(r"SystemMessage\(\s*[\"']", text):
            bad.append(f"{path.relative_to(ROOT)}: inline SystemMessage")
    if bad:
        print("\n".join(bad))
        return 1
    print(f"prompts OK ({len(list((ROOT / 'agent' / 'prompts').glob('*.md')))} prompt files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
