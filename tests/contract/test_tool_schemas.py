"""Schema snapshot test: fails CI when any MCP tool's name, input schema, output schema or
annotations change. If a change is intended, regenerate with
    UPDATE_SNAPSHOTS=1 uv run pytest tests/contract -q
and commit the new snapshot together with the change."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("APP_SECRET", "test-secret-0123456789-abcdefghijklmnop")

from mcp_servers.common import tool_snapshot  # noqa: E402

SNAP = Path(__file__).parent / "snapshots"


def servers():
    from mcp_servers.marketplace.server import mcp as marketplace
    from mcp_servers.portfolio.server import mcp as portfolio
    from mcp_servers.workspace.server import mcp as workspace

    return {"portfolio": portfolio, "marketplace": marketplace, "workspace": workspace}


@pytest.mark.parametrize("name", ["portfolio", "marketplace", "workspace"])
def test_tool_schema_snapshot(name):
    current = tool_snapshot(servers()[name])
    path = SNAP / f"{name}.json"
    if os.environ.get("UPDATE_SNAPSHOTS") == "1" or not path.exists():
        SNAP.mkdir(exist_ok=True)
        path.write_text(json.dumps(current, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        if os.environ.get("CI"):
            pytest.fail(f"snapshot {path.name} was missing in CI")
        return
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert current == saved, f"MCP tool signature of '{name}' changed; update the snapshot if intended"


def test_every_write_tool_has_idempotency_and_dry_run():
    from mcp_servers.marketplace.server import mcp

    import asyncio

    for t in asyncio.run(mcp.list_tools()):
        if t.annotations and t.annotations.readOnlyHint is False:
            props = t.inputSchema["properties"]
            assert "idempotency_key" in props and "dry_run" in props, t.name
