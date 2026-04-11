# === Stage 1: Build frontend ===
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# === Stage 2: Production image ===
FROM python:3.11-slim

LABEL maintainer="Orchestra AI"
LABEL description="Local-first multi-agent AI software development system"

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend source
COPY backend/ ./backend/
COPY prompts/ ./prompts/

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create runtime directories
RUN mkdir -p data/vector_store projects

# Serve frontend static files from FastAPI
RUN pip install --no-cache-dir aiofiles

# Expose ports
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
