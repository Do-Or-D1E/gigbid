"""MCP client setup. Every agent reaches tools through `McpGateway`:

* transport `http` uses MultiServerMCPClient over Streamable HTTP with the user's signed
  service token and the run's trace id as headers;
* transport `inproc` opens memory-stream sessions to the same FastMCP servers (tests and
  serverless), passing identity and trace id through the request _meta;
* `tools_for(agent)` returns LangChain tools filtered by the per-agent allowlist in config;
* `call()` runs one tool with a timeout and bounded retries (writes are only retried
  because they carry idempotency keys) and records a span in the execution trace;
* `MarketplaceDown` signals degraded mode so the graph can park the job and the UI can
  show the banner."""
from __future__ import annotations

import asyncio
import json
import time
from contextlib import AsyncExitStack
from typing import Any

from agent import settings, tracing
from agent.security import mint_service_token


class ToolCallError(RuntimeError):
    pass


class MarketplaceDown(ToolCallError):
    pass


SERVER_OF = {
    "search_evidence": "portfolio", "get_case_study": "portfolio", "list_skills": "portfolio",
    "free_slots": "workspace", "create_interview_hold": "workspace", "create_email_draft": "workspace",
}


def server_of(tool: str) -> str:
    return SERVER_OF.get(tool, "marketplace")


def _inproc_servers() -> dict[str, Any]:
    from mcp_servers.marketplace.server import mcp as marketplace
    from mcp_servers.portfolio.server import mcp as portfolio
    from mcp_servers.workspace.server import mcp as workspace

    return {"portfolio": portfolio, "marketplace": marketplace, "workspace": workspace}


class McpGateway:
    def __init__(self, user_id: str, persona: str | None, *, trace_id: str | None = None,
                 transport: str | None = None, scopes: list[str] | None = None) -> None:
        self.user_id = user_id
        self.persona = persona
        self.trace_id = trace_id
        self.transport = transport or settings.get("mcp.transport", "http")
        self.token = mint_service_token(user_id, user_id, persona, scopes=scopes)
        self._stack: AsyncExitStack | None = None
        self._sessions: dict[str, Any] = {}
        self._client = None

    async def __aenter__(self) -> "McpGateway":
        self._stack = AsyncExitStack()
        if self.transport == "inproc":
            from mcp.shared.memory import create_connected_server_and_client_session

            from mcp_servers.common import INPROC_AUTH, INPROC_TRACE

            INPROC_AUTH.set(self.token)
            INPROC_TRACE.set(self.trace_id)
            for name, server in _inproc_servers().items():
                self._sessions[name] = await self._stack.enter_async_context(
                    create_connected_server_and_client_session(server))
        else:
            from langchain_mcp_adapters.client import MultiServerMCPClient

            headers = {"Authorization": f"Bearer {self.token}"}
            if self.trace_id:
                headers["X-Trace-Id"] = self.trace_id
            servers = settings.get("mcp.servers")
            self._client = MultiServerMCPClient({
                name: {"transport": "streamable_http", "url": servers[name], "headers": headers,
                       "timeout": float(settings.get("marketplace.timeout_s", 15)) + 30}
                for name in ("portfolio", "marketplace", "workspace")
            })
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._stack:
            await self._stack.aclose()

    # ------------------------------------------------------------------ direct calls
    async def _call_once(self, server: str, tool: str, args: dict) -> Any:
        meta = {"auth": self.token, "trace_id": self.trace_id}
        if self.transport == "inproc":
            result = await self._sessions[server].call_tool(tool, args, meta=meta)
        else:
            async with self._client.session(server) as session:
                result = await session.call_tool(tool, args, meta=meta)
        if result.isError:
            text = " ".join(getattr(c, "text", "") for c in result.content)
            if "MARKETPLACE_UNAVAILABLE" in text:
                raise MarketplaceDown(text)
            raise ToolCallError(text[:800])
        if result.structuredContent is not None:
            sc = result.structuredContent
            return sc.get("result", sc) if isinstance(sc, dict) and set(sc) == {"result"} else sc
        text = "".join(getattr(c, "text", "") for c in result.content)
        try:
            return json.loads(text)
        except ValueError:
            return text

    async def call(self, tool: str, args: dict | None = None, *, timeout: float | None = None,
                   retries: int = 2) -> Any:
        server = server_of(tool)
        args = args or {}
        timeout = timeout or float(settings.get("marketplace.timeout_s", 15)) * 4
        t0 = time.perf_counter()
        last: Exception | None = None
        for attempt in range(retries + 1):
            try:
                out = await asyncio.wait_for(self._call_once(server, tool, args), timeout)
                tracing.add(tracing.Span("tool", tool, node=tracing.current_node.get(), args=args,
                                         result=_brief(out), latency_s=time.perf_counter() - t0))
                return out
            except MarketplaceDown as exc:
                last = exc
                break  # the server already retried GigSim; don't hammer it
            except ToolCallError as exc:
                last = exc
                if "IDEMPOTENCY_CONFLICT" in str(exc) or "REJECTED" in str(exc) or "FORBIDDEN" in str(exc):
                    break
            except Exception as exc:  # noqa: BLE001 - transport errors, timeouts
                last = exc
                if server == "marketplace" and attempt == retries:
                    last = MarketplaceDown(f"marketplace MCP server unreachable: {type(exc).__name__}: {exc}")
            if attempt < retries:
                await asyncio.sleep(0.5 * (2 ** attempt))
        tracing.add(tracing.Span("tool", tool, node=tracing.current_node.get(), args=args,
                                 error=f"{type(last).__name__}: {str(last)[:300]}", latency_s=time.perf_counter() - t0))
        if isinstance(last, (MarketplaceDown, ToolCallError)):
            raise last
        if server == "marketplace":
            raise MarketplaceDown(str(last))
        raise ToolCallError(str(last))

    # ------------------------------------------------------------------ LangChain tools
    async def tools_for(self, agent: str | None = None, names: list[str] | None = None) -> list:
        allow = set(names or settings.get("mcp.allowlists", {}).get(agent, []))
        tools: list = []
        if self.transport == "inproc":
            from langchain_mcp_adapters.tools import load_mcp_tools

            for name, session in self._sessions.items():
                tools += await load_mcp_tools(session, server_name=name)
        else:
            tools = await self._client.get_tools()
        return [t for t in tools if not allow or t.name in allow]


def _brief(out: Any) -> Any:
    text = json.dumps(out, default=str)
    return out if len(text) < 1500 else {"truncated": text[:1500]}
