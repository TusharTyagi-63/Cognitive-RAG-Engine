# ==============================================================================
# Dockerfile — Cognitive RAG Engine Backend
#
# Build:  docker build -t rag-backend .
# Run:    docker run -p 8000:8000 --env-file .env rag-backend
#
# Uses a two-stage build:
#   Stage 1 (builder): installs all dependencies into a virtual-env
#   Stage 2 (runtime): copies only the venv + source — no build tools in prod
# ==============================================================================

# ── Stage 1: Dependency Builder ───────────────────────────────────────────────
FROM python:3.11-slim AS builder

# Prevents Python from writing pyc files and enables unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install OS-level build dependencies needed by asyncpg / cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create an isolated virtual environment inside the builder stage
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install dependencies first (leverages Docker layer cache)
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


# ── Stage 2: Runtime Image ────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Minimal runtime OS deps (libpq for asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# Copy the virtual env from the builder
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Copy application source
COPY backend/ ./backend/

# Fix ownership
RUN chown -R appuser:appgroup /app

USER appuser

# Expose the application port
EXPOSE 8000

# Health check so orchestrators know when the container is ready
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run with Uvicorn — production settings
CMD ["uvicorn", "backend.app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-config", "/dev/null"]
