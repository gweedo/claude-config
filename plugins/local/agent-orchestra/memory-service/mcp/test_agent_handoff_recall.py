"""Agent-handoff recall proof (issue #24): the graph as shared memory.

The Orchestrator (docs/BUILD-PLAN.md Phase 3, ADR-0003) fans out to role
agents as **native Claude Code subagents**, each with an isolated context.
They cannot see each other's conversation — the Context graph is the only
channel between them. This test proves that channel over the exact same MCP
tool contract the live `orchestrator` skill uses (`memory_write` /
`memory_query`), without needing to actually spawn Claude subagents:

  1. A "Developer" identity writes a decision triple at handoff, exactly as
     `agents/developer.md` instructs (memory_write).
  2. A "Architect" identity — a completely separate MCP session, standing in
     for the isolated subagent context the real Architect subagent would run
     in — queries for that subject and must recall the Developer's triple, as
     `agents/architect.md` / `skills/orchestrator/SKILL.md` instruct
     (memory_query before doing its own work).

Two independent stdio MCP client sessions are used (not one shared session)
so the proof does not depend on any in-process state a single session might
retain — it goes through Postgres, matching how two real, isolated subagents
would actually communicate.

Runs inside the MCP image against the live postgres service:
    docker compose --profile test run --rm mcp-test
"""

from __future__ import annotations

import json
import os
import uuid

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _server_params() -> StdioServerParameters:
    # Forward MEMORY_DATABASE_URL so each spawned server reaches the same DB.
    # stdio_client starts the server with a minimal env, so pass it explicitly.
    return StdioServerParameters(
        command="python",
        args=["server.py"],
        env={"MEMORY_DATABASE_URL": os.environ["MEMORY_DATABASE_URL"]},
    )


async def _run() -> None:
    subject = f"RateLimiter-{uuid.uuid4().hex[:8]}"

    # --- Developer subagent's handoff: writes its decision, then exits. ---
    # A fresh stdio session per role stands in for each subagent's isolated
    # process/context — nothing in-process is shared between the two.
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as developer_session:
            await developer_session.initialize()
            await developer_session.call_tool(
                "memory_write",
                {
                    "triples": [
                        {
                            "subject": subject,
                            "predicate": "IMPLEMENTED_WITH",
                            "object": "token-bucket algorithm",
                        }
                    ]
                },
            )
    # The Developer session is now closed — its context is gone, exactly like
    # a completed subagent. Only the graph remembers what it decided.

    # --- Architect subagent, later, in a brand-new isolated session: must
    # recall the Developer's decision before doing its own review. ---
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as architect_session:
            await architect_session.initialize()
            result = await architect_session.call_tool(
                "memory_query", {"subject": subject}
            )
            payload = json.loads(result.content[0].text)

            assert len(payload) == 1, payload
            assert payload[0]["subject"] == subject
            assert payload[0]["predicate"] == "IMPLEMENTED_WITH"
            assert payload[0]["object"] == "token-bucket algorithm"

    print(
        "Agent-handoff recall OK: a later (Architect) session recalled an "
        "earlier (Developer) session's decision via memory_query — the graph "
        "is shared memory across isolated subagent contexts."
    )


def test_later_agent_recalls_earlier_agents_decision_across_isolated_sessions() -> None:
    anyio.run(_run)


if __name__ == "__main__":
    anyio.run(_run)
