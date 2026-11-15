"""GigBid Portfolio MCP server (read-only).

Run standalone for Claude Desktop / Cursor (stdio):
    uv run python -m mcp_servers.portfolio.server --stdio --owner ai_ml
Run as an authenticated HTTP server for GigBid (Streamable HTTP at /mcp):
    uv run python -m mcp_servers.portfolio.server --port 8101
"""
from __future__ import annotations

import argparse
import os
from typing import Annotated

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_servers import common
from mcp_servers.portfolio import prompts as P
from mcp_servers.portfolio import resources as R
from mcp_servers.portfolio import tools as T

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)

mcp = FastMCP(
    "gigbid-portfolio",
    instructions=("Read-only access to a freelancer's portfolio: CV, case studies, repositories, client reviews "
                  "and past proposals with outcomes. Use search_evidence to find proof for a job requirement, "
                  "then load full items with get_case_study or the portfolio:// resources."),
    stateless_http=True,
    json_response=True,
)


def _owner(ctx: Context) -> tuple[str, str | None]:
    who = common.identity(ctx, required=os.environ.get("PORTFOLIO_REQUIRE_AUTH", "0") == "1")
    return who.get("persona") or os.environ.get("PORTFOLIO_OWNER", "ai_ml"), who.get("sub")


@mcp.tool(annotations=READ_ONLY, title="Search portfolio evidence")
async def search_evidence(
    requirement: Annotated[str, Field(min_length=2, max_length=300,
                                      description="One job requirement, e.g. 'Celery task queues for ETL'")],
    ctx: Context,
    k: Annotated[int, Field(ge=1, le=15, description="How many evidence items to return")] = 5,
    filters: T.EvidenceFilters | None = None,
) -> T.EvidenceResults:
    """Find the portfolio items (case studies, repos, reviews, past proposals, CV) that best prove the
    freelancer can meet ONE requirement. Returns each item's id, type, source, date and, for past
    proposals, the outcome (won/replied/ignored)."""
    owner, user = _owner(ctx)
    res = await T.search_evidence(owner, requirement, k, filters, user_id=user)
    common.audit("portfolio", "search_evidence", user, {"requirement": requirement, "k": k},
                 {"items": [i.item_id for i in res.items]}, common.trace_id(ctx))
    return res


@mcp.tool(annotations=READ_ONLY, title="Get one portfolio item")
def get_case_study(
    item_id: Annotated[str, Field(min_length=3, max_length=80, pattern=r"^[\w\-.#]+$",
                                  description="Portfolio item id, e.g. 'ai_ml-cs-07' or 'ai_ml-repo-03'")],
    ctx: Context,
) -> T.CaseStudy:
    """Load the full text and metadata of one portfolio item (case study, repo, review, proposal or CV)."""
    owner, user = _owner(ctx)
    return T.get_case_study(owner, item_id.split("#")[0], user_id=user)


@mcp.tool(annotations=READ_ONLY, title="List skills")
def list_skills(ctx: Context) -> T.SkillList:
    """List the skills on the freelancer's profile and how many portfolio items mention each skill by name."""
    owner, _ = _owner(ctx)
    return T.list_skills(owner)


R.register(mcp, _owner)
P.register(mcp)


def http_app(require_auth: bool = True):
    return common.BearerGuard(mcp.streamable_http_app(), required=require_auth)


def main() -> None:
    parser = argparse.ArgumentParser(description="GigBid portfolio MCP server")
    parser.add_argument("--stdio", action="store_true", help="serve over stdio (Claude Desktop, Cursor)")
    parser.add_argument("--owner", default=os.environ.get("PORTFOLIO_OWNER", "ai_ml"),
                        help="persona/portfolio folder under data/personas")
    parser.add_argument("--port", type=int, default=8101)
    parser.add_argument("--no-auth", action="store_true")
    args = parser.parse_args()
    os.environ["PORTFOLIO_OWNER"] = args.owner
    if args.stdio:
        mcp.run("stdio")
        return
    import uvicorn

    if not args.no_auth:
        os.environ["PORTFOLIO_REQUIRE_AUTH"] = "1"
    uvicorn.run(http_app(not args.no_auth), host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
