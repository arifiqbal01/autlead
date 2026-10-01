# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Runtime/build dependencies.
#
# curl:
#   installs uv
#
# docker.io:
#   required because some Autlead providers currently execute
#   external Docker images through the Docker CLI.
#
# Playwright installs its own browser/system dependencies below.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        docker.io \
    && rm -rf /var/lib/apt/lists/*

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency metadata first so Docker can cache dependency installation.
COPY pyproject.toml uv.lock README.md ./

# Install production dependencies only.
RUN uv sync \
    --frozen \
    --no-dev \
    --no-install-project

# Copy application/package sources.
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts

# Install the Autlead package itself.
RUN uv sync \
    --frozen \
    --no-dev

# Install Chromium and the Linux libraries required by Playwright.
RUN playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

# Persistent/runtime directories.
RUN mkdir -p \
    /app/data \
    /app/logs \
    /app/output

# Default command is deliberately harmless.
# Actual acquisition/enrichment commands can be supplied through
# docker compose run/exec until we settle on the permanent worker command.
CMD ["python", "-m", "app.main"]