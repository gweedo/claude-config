# Memory MCP server image. The server runs as a local stdio process (ADR-0002);
# containerizing it keeps the runtime fully reproducible and independent of the
# host Python version. Claude Code launches it via `docker compose run` (see the
# MCP config in the plugin README).
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the server, its store, and the integration tests. Globbing the test
# files keeps the build from needing an edit each time a test is added (#22).
COPY memory_store.py server.py test_*.py ./

# stdio transport — no ports exposed.
CMD ["python", "server.py"]
