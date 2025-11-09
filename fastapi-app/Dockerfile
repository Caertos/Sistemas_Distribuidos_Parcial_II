# =============================================================================
# Multi-stage Dockerfile for FastAPI FHIR Application
# Optimized for production deployment with minimal image size
# =============================================================================

# Stage 1: Build stage with development dependencies
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies required for building
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /build

# Copy requirements first for better Docker layer caching
COPY requirements.txt requirements-dev.txt ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements-dev.txt

# Copy application source code
COPY . .

# Run tests and linting (optional - can be disabled for faster builds)
# RUN python -m pytest tests/ -v
# RUN python -m flake8 app/
# RUN python -m mypy app/

# =============================================================================
# Stage 2: Production stage with minimal dependencies
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH="/app" \
    PORT=8000

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    libffi7 \
    libssl1.1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create application directory and logs directory
RUN mkdir -p /app/logs && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application code
COPY --chown=appuser:appuser . .

# Ensure logs directory has correct permissions
RUN chmod 755 /app/logs

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# =============================================================================
# Stage 3: Development stage (optional)
FROM builder as development

# Install additional development tools
RUN pip install --no-cache-dir \
    debugpy \
    ipython \
    jupyter

# Set development environment
ENV ENVIRONMENT=development \
    DEBUG=true \
    LOG_LEVEL=debug

# Expose additional ports for debugging
EXPOSE 8000 5678

# Development command with auto-reload
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]