# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS uv

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
# ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Set build argument
ARG DEBUG

# Set environment variable based on the build argument
ENV DEBUG=${DEBUG}

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    git \
    curl \
    cmake \
    clang \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and lockfile first for better caching
COPY README.md pyproject.toml uv.lock entrypoint.sh ./

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --extra debug --extra api --extra postgres --extra neo4j --extra llama-index --extra ollama --extra mistral --extra groq --extra anthropic --frozen --no-install-project --no-dev --no-editable

# Copy Alembic configuration (both the base and the Enhanced PostgreSQL schema).
# entrypoint.sh runs `alembic -c alembic-enhanced.ini upgrade head` when
# ENHANCED_RUN_MIGRATIONS=1, so the enhanced config + its versions must be here.
COPY alembic.ini /app/alembic.ini
COPY alembic/ /app/alembic
COPY alembic-enhanced.ini /app/alembic-enhanced.ini
COPY alembic_enhanced/ /app/alembic_enhanced

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching.
# src/ holds the RNR Enhanced Cognee FastAPI app (src.enhanced_cognee_mcp:app) that
# entrypoint.sh launches -- it MUST be copied or the container exits on start.
COPY ./src /app/src
COPY ./cognee /app/cognee
COPY ./distributed /app/distributed
RUN --mount=type=cache,target=/root/.cache/uv \
uv sync --extra debug --extra api --extra postgres --extra neo4j --extra llama-index --extra ollama --extra mistral --extra groq --extra anthropic --frozen --no-dev --no-editable

# Pinned runtime base: Python 3.12 on Debian Bookworm slim.
FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=uv /app /app
# COPY --from=uv /app/.venv /app/.venv
# COPY --from=uv /root/.local /root/.local

# Normalize line endings (strip any CR introduced by Windows/git autocrlf) and
# mark the entrypoint executable so `/bin/sh` can run it inside the container.
RUN sed -i 's/\r$//' /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

# Create a non-root user and hand it ownership of the app tree.
RUN groupadd --system appuser \
    && useradd --system --gid appuser --create-home --home-dir /home/appuser appuser \
    && chown -R appuser:appuser /app

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

ENV PYTHONPATH=/app
# ENV LOG_LEVEL=ERROR
ENV PYTHONUNBUFFERED=1

# Drop privileges -- the app runs as the unprivileged appuser.
USER appuser

ENTRYPOINT ["/app/entrypoint.sh"]
