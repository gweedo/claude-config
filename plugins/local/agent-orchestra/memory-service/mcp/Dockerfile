# Memory MCP server image. The server runs as a local stdio process (ADR-0002);
# containerizing it keeps the runtime fully reproducible and independent of the
# host Python version. Claude Code launches it via `docker compose run` (see the
# MCP config in the plugin README).
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the local embedding model at build time (#23) so container
# startup and test runs never hit the network — the weights are baked into the
# image, keeping the Memory service fully local (ADR-0002).
ENV SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence-transformers
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Force offline mode at runtime: without this, huggingface_hub still makes
# HEAD requests to check for model updates on every load, even though the
# weights are already cached above. The Memory service must not depend on
# network access to serve a query (ADR-0002).
ENV HF_HUB_OFFLINE=1
ENV TRANSFORMERS_OFFLINE=1

# Copy the server, its store, and the integration tests. Globbing the test
# files keeps the build from needing an edit each time a test is added (#22).
COPY memory_store.py server.py test_*.py ./

# stdio transport — no ports exposed.
CMD ["python", "server.py"]
