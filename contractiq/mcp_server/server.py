"""MCP tool server entry point (SRS FR-7).

Exposes the five structured tools two ways:

1. **Native MCP** over stdio when the ``mcp`` SDK is installed
   (``python -m contractiq.mcp_server.server``), so any MCP-capable agent/host
   can call them.
2. **REST** via a FastAPI sub-application mounted by the main API, so the
   tools are callable over HTTP and unit-testable without an MCP host.

Both paths share the same tool functions and schemas, guaranteeing identical
behaviour. Every tool returns structured JSON; errors include ``error_message``.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core.logging import get_logger
from .schemas import TOOL_SCHEMAS
from .tools import TOOLS

log = get_logger("mcp_server")


# --- REST surface (mounted by the main API at /mcp) -------------------------

router = APIRouter(prefix="/mcp", tags=["mcp"])


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = {}


@router.get("/tools")
def list_tools() -> dict:
    """Advertise available tools and their JSON schemas (SRS FR-7)."""
    return {
        "tools": [
            {"name": name, **TOOL_SCHEMAS[name]} for name in TOOLS if name in TOOL_SCHEMAS
        ]
    }


@router.post("/call")
def call_tool(call: ToolCall) -> dict:
    """Invoke a tool by name with keyword arguments."""
    fn = TOOLS.get(call.name)
    if fn is None:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {call.name}")
    try:
        result = fn(**call.arguments)
    except TypeError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid arguments: {exc}")
    return {"tool": call.name, "result": result}


# --- Native MCP server (stdio) ---------------------------------------------

def run_stdio() -> None:  # pragma: no cover - requires mcp SDK + host
    """Run as a native MCP server over stdio."""
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception as exc:
        raise SystemExit(
            "The 'mcp' SDK is not installed. Install it (`pip install mcp`) to run "
            f"the native MCP server, or use the REST surface instead. ({exc})"
        )

    mcp = FastMCP("contractiq")
    for name, fn in TOOLS.items():
        mcp.tool(name=name, description=TOOL_SCHEMAS.get(name, {}).get("description", ""))(fn)
    log.info("Starting ContractIQ MCP server (stdio) with %d tools", len(TOOLS))
    mcp.run()


if __name__ == "__main__":  # pragma: no cover
    run_stdio()
