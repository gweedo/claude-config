"""Proof that memory_supersede is callable over the MCP stdio transport (#22).

Spawns server.py as a real stdio MCP server and, via the MCP client SDK:
  1. lists tools -> confirms `memory_supersede` is exposed alongside the others,
  2. writes a fact, supersedes it, re-queries -> confirms the stale fact is gone
     through the actual MCP tool interface (not just the store).

Runs as part of the `mcp-test` suite against the live postgres service:
    docker compose --profile test run --rm mcp-test
"""

from __future__ import annotations

import json
import os
import uuid

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def _run() -> None:
    params = StdioServerParameters(
        command="python",
        args=["server.py"],
        env={"MEMORY_DATABASE_URL": os.environ["MEMORY_DATABASE_URL"]},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = {t.name for t in (await session.list_tools()).tools}
            assert "memory_supersede" in tools, tools

            subject = f"AuthModule-{uuid.uuid4().hex[:8]}"
            await session.call_tool(
                "memory_write",
                {"triples": [{"subject": subject, "predicate": "USES", "object": "Sessions"}]},
            )
            await session.call_tool(
                "memory_supersede",
                {"subject": subject, "predicate": "USES", "object": "Sessions"},
            )
            await session.call_tool(
                "memory_write",
                {"triples": [{"subject": subject, "predicate": "USES", "object": "JWT"}]},
            )

            result = await session.call_tool("memory_query", {"subject": subject})
            payload = json.loads(result.content[0].text)
            objects = {row["object"] for row in payload["triples"]}
            assert objects == {"JWT"}, payload

    print("MCP supersede round-trip OK: memory_supersede exposed and stale fact hidden")


def test_mcp_supersede_round_trip() -> None:
    anyio.run(_run)


if __name__ == "__main__":
    anyio.run(_run)
