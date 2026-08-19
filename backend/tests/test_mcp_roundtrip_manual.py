"""Standalone script (not part of the pytest suite) that spawns the MCP
server as a real stdio subprocess and calls a tool through an actual MCP
ClientSession - verifies the server is wired correctly end to end, not just
that the underlying functions work.

Run: python tests/test_mcp_roundtrip_manual.py (from backend/)
"""
import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    params = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("tools:", [t.name for t in tools.tools])

            result = await session.call_tool("get_cell_status_tool", {"cell_id": "KOL-5G-017"})
            print("get_cell_status_tool ->", result.content[0].text if result.content else result)

            result = await session.call_tool(
                "search_knowledge_base_tool", {"query": "congestion PRB troubleshooting", "top_k": 2}
            )
            print("search_knowledge_base_tool ->", result.content[0].text[:200] if result.content else result)


if __name__ == "__main__":
    asyncio.run(main())
