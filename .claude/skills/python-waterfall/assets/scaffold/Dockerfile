# syntax=docker/dockerfile:1
# Phase 5, only when 02-design.md chose a container target. Multi-stage build per
# uv's Docker guide: dependencies are a cached layer, the runtime image has no uv,
# no build tools and runs as a non-root user. Replace PACKAGE / the CMD.
ARG PYTHON_VERSION=3.14

FROM ghcr.io/astral-sh/uv:0.13-python${PYTHON_VERSION}-trixie-slim AS builder
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

FROM python:${PYTHON_VERSION}-slim-trixie
RUN groupadd --system --gid 999 app \
 && useradd --system --gid 999 --uid 999 --no-create-home app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
USER app
WORKDIR /app
# Web API example: CMD ["uvicorn", "PACKAGE.main:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["PACKAGE"]
