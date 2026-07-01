"""Proof that the MCP server registers and exposes its tools over stdio.

Spawns server.py as a real stdio MCP server and, via the MCP client SDK:
  1. lists tools -> confirms `memory_write` and `memory_query` are exposed,
  2. calls `memory_write` then `memory_query` -> confirms a written triple
     round-trips through the actual MCP tool interface (not just the store).

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
    # Forward MEMORY_DATABASE_URL so the spawned server reaches the same DB.
    # stdio_client starts the server with a minimal env, so pass it explicitly.
    params = StdioServerParameters(
        command="python",
        args=["server.py"],
        env={"MEMORY_DATABASE_URL": os.environ["MEMORY_DATABASE_URL"]},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = {t.name for t in (await session.list_tools()).tools}
            assert "memory_write" in tools, tools
            assert "memory_query" in tools, tools

            subject = f"PaymentService-{uuid.uuid4().hex[:8]}"
            await session.call_tool(
                "memory_write",
                {
                    "triples": [
                        {
                            "subject": subject,
                            "predicate": "EMITS",
                            "object": "PaymentReceived",
                        }
                    ]
                },
            )

            result = await session.call_tool("memory_query", {"subject": subject})
            payload = json.loads(result.content[0].text)
            triples = payload["triples"]
            assert len(triples) == 1, payload
            assert triples[0]["subject"] == subject
            assert triples[0]["predicate"] == "EMITS"
            assert triples[0]["object"] == "PaymentReceived"

    print("MCP protocol round-trip OK: memory_write + memory_query exposed and working")


def test_mcp_tools_round_trip() -> None:
    anyio.run(_run)


if __name__ == "__main__":
    anyio.run(_run)
