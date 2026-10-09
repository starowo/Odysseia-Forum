# ============================================================
# base — 仅安装核心依赖，用于正常启动 Bot
# ============================================================
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl procps libjemalloc2 libpq-dev postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/lib/*/libjemalloc.so.2 /usr/lib/libjemalloc.so.2

ENV LD_PRELOAD=/usr/lib/libjemalloc.so.2 \
    MALLOC_CONF="narenas:2"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

COPY src ./src
COPY bot_main.py ./
COPY healthcheck.py ./
COPY api_main.py ./
COPY alembic.ini ./
COPY alembic ./alembic

COPY scripts ./scripts

RUN mkdir -p /app/data /app/logs

# ============================================================
# dev — 基于 base，额外安装 dev 依赖（pytest、ruff 等）
# ============================================================
FROM base AS dev

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --extra dev --no-install-project
