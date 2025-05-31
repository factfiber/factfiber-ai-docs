# Multi-stage Dockerfile for FactFiber Documentation Infrastructure
# Optimized for development and production use

# Build stage
FROM python:3.13-slim as builder

# Set build arguments
ARG POETRY_VERSION=1.8.0
ARG ENVIRONMENT=production

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==$POETRY_VERSION

# Set Poetry configuration
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install --without dev && rm -rf $POETRY_CACHE_DIR

# Production stage
FROM python:3.13-slim as production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r ffuser && useradd -r -g ffuser ffuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src/ ./src/
COPY docs/ ./docs/
COPY mkdocs.yml ./
COPY README.md ./
COPY LICENSE ./

# Create necessary directories
RUN mkdir -p /tmp/ff-docs /app/logs && \
    chown -R ffuser:ffuser /app /tmp/ff-docs

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src:$PYTHONPATH" \
    ENVIRONMENT=production \
    DEBUG=false

# Switch to non-root user
USER ffuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Expose ports
EXPOSE 8000 8001

# Default command
CMD ["python", "-m", "uvicorn", "ff_docs.server.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Development stage
FROM production as development

# Switch back to root for installing dev dependencies
USER root

# Install development tools
RUN apt-get update && apt-get install -y \
    vim \
    less \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy poetry files and install dev dependencies
COPY pyproject.toml poetry.lock ./
RUN python -m pip install poetry && \
    poetry install --with dev && \
    rm -rf ~/.cache/pypoetry

# Switch back to non-root user
USER ffuser

# Override environment for development
ENV ENVIRONMENT=development \
    DEBUG=true \
    RELOAD=true

# Development command with hot reloading
CMD ["python", "-m", "uvicorn", "ff_docs.server.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]