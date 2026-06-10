"""MCP server wiring (SRS FR-7) — powered by ``fastapi-mcp``.

Instead of hand-writing an MCP transport and JSON schemas, we let ``fastapi-mcp``
turn the tool endpoints in :mod:`contractiq.mcp_server.router` into a real MCP
server (Streamable HTTP) mounted at ``/mcp``. Schemas are generated from the
endpoints' Pydantic models, so they can't drift from the implementation.

External MCP hosts (e.g. Claude Desktop) connect to ``http://<host>/mcp``.
"""
from __future__ import annotations

from fastapi import FastAPI

from ..core.logging import get_logger

log = get_logger("mcp_server")

MCP_NAME = "ContractIQ"
MCP_DESCRIPTION = (
    "Legal contract analysis tools: clause extraction, risk scoring, plain-English "
    "legal definitions, clause comparison, and industry benchmarks."
)


def setup_mcp(app: FastAPI):
    """Build and mount the MCP server from the app's ``tools``-tagged endpoints.

    Must be called *after* the tools router is registered on ``app``. Returns the
    ``FastApiMCP`` instance (also stored on ``app.state.mcp``) so callers/tests can
    introspect the generated tools.
    """
    from fastapi_mcp import FastApiMCP

    mcp = FastApiMCP(
        app,
        name=MCP_NAME,
        description=MCP_DESCRIPTION,
        include_tags=["tools"],  # expose only the 5 FR-7 tools as MCP tools
    )
    mcp.mount_http()  # Streamable HTTP transport at /mcp
    app.state.mcp = mcp
    log.info("Mounted MCP server '%s' at /mcp with %d tools: %s",
             MCP_NAME, len(mcp.tools), ", ".join(t.name for t in mcp.tools))
    return mcp
