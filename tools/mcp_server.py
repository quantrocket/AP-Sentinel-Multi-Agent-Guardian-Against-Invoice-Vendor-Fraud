"""
MCP server exposing AP Sentinel's verified tool set (vendor lookup, bank-change
history, sanctions screening, policy retrieval, risk scoring) over the open
Model Context Protocol.

Two consumers, both Google-ecosystem:
1. The Independent Verification agent (agents/independent_verifier.py) can be
   pointed at this server so its re-check calls the exact same verified tools
   the main pipeline used, rather than trusting a paraphrased summary.
2. Any MCP-compatible IDE or external agent (Google Antigravity, Gemini CLI,
   Cursor, etc.) can attach to this server directly to query AP Sentinel's
   fraud-signal tools from outside the pipeline -- the same "expose tools over
   MCP" pattern used by Lighthouse Agentic Hub's mcp_server.py, applied here
   to finance/AP tooling instead of web-readiness auditing.

MCP itself is an open, vendor-neutral protocol (not tied to any single model
provider), so exposing tools this way keeps the project fully Google-native
while still being interoperable with any MCP client.

Run standalone: `python tools/mcp_server.py` (listens on :8765)
"""
from mcp.server.fastmcp import FastMCP
from tools.function_tools import (
    vendor_lookup, bank_change_lookup, sanctions_check, retrieve_policy, risk_score,
)

mcp = FastMCP("ap-sentinel-tools")

mcp.tool()(vendor_lookup)
mcp.tool()(bank_change_lookup)
mcp.tool()(sanctions_check)
mcp.tool()(retrieve_policy)
mcp.tool()(risk_score)

if __name__ == "__main__":
    mcp.run(transport="sse", port=8765)
