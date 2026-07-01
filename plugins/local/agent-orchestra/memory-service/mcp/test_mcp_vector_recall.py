"""Proof that vector recall is callable over the MCP stdio transport (#23).

Spawns server.py as a real stdio MCP server and, via the MCP client SDK:
  1. calls `memory_write` with a `chunks` payload -> confirms free text can be
     stored through the actual MCP tool interface (not just the store),
  2. calls `memory_query` with a `text` payload -> confirms a semantically
     related (not exact-string) query surfaces it, and that graph recall
     (`subject`) and vector recall (`text`) can be requested in the same call
     against the same live container.

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
            assert "memory_write" in tools, tools
            assert "memory_query" in tools, tools

            tag = uuid.uuid4().hex[:8]
            subject = f"RateLimiter-{tag}"

            # Write both a triple and a chunk in one call.
            await session.call_tool(
                "memory_write",
                {
                    "triples": [
                        {"subject": subject, "predicate": "USES", "object": "TokenBucket"}
                    ],
                    "chunks": [
                        {
                            "text": f"{subject} throttles incoming API requests to "
                            "prevent abuse and protect downstream services."
                        }
                    ],
                },
            )

            # Query both recall modes in one call against the same container.
            result = await session.call_tool(
                "memory_query",
                {"subject": subject, "text": f"How does {subject} stop excessive traffic?"},
            )
            payload = json.loads(result.content[0].text)

            assert payload["triples"][0]["object"] == "TokenBucket", payload
            assert any(subject in c["text"] for c in payload["chunks"]), payload

    print("MCP vector-recall round-trip OK: memory_write/memory_query chunks exposed and working")


async def _run_empty_query_rejected() -> None:
    """memory_query with neither `subject` nor `text` errors instead of
    silently returning `{}` — a caller typo (e.g. a misspelled kwarg) must
    surface immediately, not look like an empty-but-successful result."""
    params = StdioServerParameters(
        command="python",
        args=["server.py"],
        env={"MEMORY_DATABASE_URL": os.environ["MEMORY_DATABASE_URL"]},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("memory_query", {})
            assert result.isError, result


def test_mcp_query_with_no_recall_target_errors() -> None:
    anyio.run(_run_empty_query_rejected)


def test_mcp_vector_recall_round_trip() -> None:
    anyio.run(_run)


if __name__ == "__main__":
    anyio.run(_run)
