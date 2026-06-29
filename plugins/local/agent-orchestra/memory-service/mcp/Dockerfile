# Memory MCP server image. The server runs as a local stdio process (ADR-0002);
# containerizing it keeps the runtime fully reproducible and independent of the
# host Python version. Claude Code launches it via `docker compose run` (see the
# MCP config in the plugin README).
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY memory_store.py server.py test_store_then_read.py test_mcp_protocol.py ./

# stdio transport — no ports exposed.
CMD ["python", "server.py"]
