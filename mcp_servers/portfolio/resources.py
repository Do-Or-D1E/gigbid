"""Resource templates so a host can load whole portfolio items."""
from __future__ import annotations

import json

from mcp.server.fastmcp import Context, FastMCP

from mcp_servers.portfolio import tools as T


def register(mcp: FastMCP, owner_of) -> None:
    @mcp.resource("portfolio://case/{item_id}", mime_type="text/markdown", title="Case study")
    def case(item_id: str) -> str:
        """Full case study as Markdown."""
        return _render(item_id)

    @mcp.resource("portfolio://proposal/{item_id}", mime_type="text/markdown", title="Past proposal")
    def proposal(item_id: str) -> str:
        """A past proposal with its job summary and outcome."""
        return _render(item_id)

    @mcp.resource("portfolio://repo/{item_id}", mime_type="text/markdown", title="Repository")
    def repo(item_id: str) -> str:
        """Repository README and code files."""
        return _render(item_id)

    @mcp.resource("portfolio://profile", mime_type="application/json", title="Profile")
    def profile() -> str:
        """Freelancer profile: skills, rates, availability."""
        import os

        from rag.ingest.loaders import PERSONA_DIR

        owner = os.environ.get("PORTFOLIO_OWNER", "ai_ml")
        path = PERSONA_DIR / owner / "profile.json"
        return path.read_text(encoding="utf-8") if path.exists() else json.dumps({"owner": owner})


def _render(item_id: str) -> str:
    import os

    from rag.ingest.loaders import list_personas

    owner = next((p for p in list_personas() if item_id.startswith(p + "-")),
                 os.environ.get("PORTFOLIO_OWNER", "ai_ml"))
    item = T.get_case_study(owner, item_id)
    head = f"# {item.title}\n\n- id: {item.item_id}\n- type: {item.type}\n- date: {item.date}\n"
    head += f"- industry: {item.client_industry}\n- source: {item.source}\n\n"
    return head + item.text
