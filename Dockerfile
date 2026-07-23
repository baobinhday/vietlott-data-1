# =============================================================================
# Stage 1 — Frontend build (Vite + TypeScript)
# =============================================================================
FROM node:20-alpine AS builder

WORKDIR /app/web

# Install dependencies first (cache-friendly)
# No package-lock.json in this project, so `npm install` is used.
# If a lockfile is added in the future, add a COPY for it and switch to:
#   RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY web/package.json ./
RUN npm install

# Copy the rest of the frontend source and build
COPY web/ .
RUN npm run build

# =============================================================================
# Stage 2 — Python runtime
# =============================================================================
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

# Copy built frontend from Stage 1
COPY --from=builder /app/web/dist /app/web/dist

# Mount point for runtime data (mounted read-only via compose)
RUN mkdir -p /app/data && chown appuser:appgroup /app/data

EXPOSE 8000

# Switch to non-root user
USER appuser

# Run the FastAPI application
CMD ["uv", "run", "uvicorn", "vietlott.web_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
