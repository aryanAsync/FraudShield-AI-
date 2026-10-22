# FraudShield AI — Machine Learning Service Dockerfile
# Multi-stage / optimized slim production container for FastAPI inference

FROM python:3.11-slim AS runtime

# Prevents Python from writing pyc files to disc and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    ENVIRONMENT=production

# Install curl for health check and essential system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-privileged user to run the service securely
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

# Install Python dependencies first for caching efficiency
COPY requirements.txt pyproject.toml /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app /app/app

# Create artifacts directory and copy pre-trained model bundle
# Note: Model artifacts can also be supplied/mounted dynamically via volume:
#   docker run -v $(pwd)/artifacts:/app/artifacts:ro ...
COPY artifacts /app/artifacts

# Grant ownership to non-root user
RUN chown -R appuser:appgroup /app

USER appuser

# Expose standard FastAPI application port
EXPOSE 8000

# Container healthcheck using standard curl against /health
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Launch production ASGI server with multiple workers
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
