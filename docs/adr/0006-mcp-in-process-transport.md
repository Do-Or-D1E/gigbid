# ADR 0006: An in-process transport for the MCP servers

Status: accepted

## Context

All tools reach agents through MCP. Normally that means separate servers over HTTP. On Vercel there is one function, so separate servers are not possible. Tests also benefit from not starting processes. We still want the same tool code, schemas, annotations, validation and audit in every mode.

## Decision

- The three FastMCP servers are plain Python objects (`mcp` in each `server.py`). `McpGateway` in `agent/mcp_client.py` supports two transports, set by `mcp.transport` or `MCP_TRANSPORT`:
  - `http`: Streamable HTTP to the servers, with the signed service token and the trace id as headers.
  - `inproc`: memory-stream sessions to the same FastMCP objects (`create_connected_server_and_client_session`). The token and trace id go in the request `_meta` and in context variables.
- Every call still goes through the MCP protocol layer, so input validation, output schemas, annotations, the `write` scope check, rate limiting, idempotency and the audit log behave the same.
- The servers are also mounted at `/mcp/portfolio`, `/mcp/marketplace` and `/mcp/workspace` in the API app, behind `BearerGuard`, so an external MCP client can still use them over HTTP.
- A contract test snapshots every tool's name, schemas and annotations (`tests/contract/`), so the two transports cannot drift apart.

## Consequences

- One tool implementation, three modes: separate processes, one process on Vercel, and tests.
- In `inproc` mode the servers share a process and a failure domain with the API. A bug in a tool can affect the API.
- Process isolation, which is a reason to use MCP over plain function calls, is not present in that mode. The protocol boundary and the checks are still there.
- Identity passing differs per transport, so `identity()` has three sources (`_meta`, header, context variable). This is more code to test.
