# =============================================================================
# Stage 1 — Python runtime (API-only mode)
# =============================================================================
# Note: the Next.js frontend in web/ is a full-stack app (server-side API
# routes reading data/ via node:fs) and cannot be baked as a static SPA into
# this image. Run it separately with `make run-web`. This image serves the
# FastAPI backend in API-only mode.
FROM python:3.11-slim

# Install uv package manager
RUN pip install --no-cache-dir uv

# Create a non-root user for runtime
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser

WORKDIR /app

# Copy dependency manifests
COPY pyproject.toml uv.lock* ./

# Install Python dependencies (web extra only — no dev/ml)
RUN uv sync --extra web --no-dev --frozen

# Copy application source code
COPY src/ ./src/

# Mount point for runtime data (mounted read-only via compose)
RUN mkdir -p /app/data && chown appuser:appgroup /app/data

EXPOSE 8000

# Switch to non-root user
USER appuser

# Run the FastAPI application
CMD ["uv", "run", "uvicorn", "vietlott.web_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
