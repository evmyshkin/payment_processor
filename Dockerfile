# ===============================================
# BASE IMAGE: Python 3.14-alpine + uv
# ===============================================
FROM ghcr.io/astral-sh/uv:python3.14-alpine AS python-base

ENV UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PROJECT_PATH="/app" \
    UV_COMPILE_BYTECODE=1 \
    PYTHONOPTIMIZE=1 \
    PYTHONUNBUFFERED=1

WORKDIR $PROJECT_PATH


# =====================================================
# DEPENDENCY BUILDER BASE
# =====================================================
FROM python-base AS deps-base

# Build deps are installed only for builder stages.
RUN apk --no-cache add \
    build-base=0.5-r3 \
    file=5.46-r2

COPY pyproject.toml uv.lock ./


# =====================================================
# BUILD (production) without dev dependencies
# =====================================================
FROM deps-base AS build-production-image

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --verbose --no-install-project

# Copy only runtime-required files to keep production layers small.
COPY app ./app
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --verbose


# =====================================================
# BUILD (dev)
# =====================================================
FROM deps-base AS build-dev-image

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --verbose --no-install-project

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --verbose


# =====================================================
# RUNTIME BASE
# =====================================================
FROM python-base AS runtime-base

# Runtime libs only (python-magic requires libmagic from file package).
RUN addgroup -g 2000 user && \
    adduser -u 2000 -S user -G user -s /bin/sh -h /home/user && \
    apk --no-cache add \
        file=5.46-r2 \
        libgcc=15.2.0-r2 \
        libstdc++=15.2.0-r2 && \
    mkdir -p "$PROJECT_PATH" && chown user:user "$PROJECT_PATH"

USER user
WORKDIR /app


# =====================================================
# IMAGE (production)
# =====================================================
FROM runtime-base AS production-image

ENV PRODUCTION=True

COPY --from=build-production-image --chown=user:user /app /app

CMD ["/app/.venv/bin/uvicorn", "app.main:fastapi_app", "--host", "0.0.0.0", "--port", "8000"]


# =====================================================
# IMAGE (dev) with hot-reload
# =====================================================
FROM runtime-base AS dev-image

ENV PRODUCTION=False

COPY --from=build-dev-image --chown=user:user /app /app

CMD ["/app/.venv/bin/uvicorn", "app.main:fastapi_app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
