# Multi-stage: build the Vue SPA, then serve API + built SPA from one FastAPI app.

# ---- Stage 1: build the Vue frontend ----
FROM node:20-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python runtime ----
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application code (only what the server needs at runtime).
COPY config.py ./
COPY api/ ./api/
COPY rag/ ./rag/
COPY ingestion/ ./ingestion/

# Built SPA from stage 1 → served by FastAPI's history-mode fallback (api/main.py
# resolves <repo>/frontend/dist relative to api/main.py).
COPY --from=frontend /frontend/dist ./frontend/dist

# Run as a non-root user (defense-in-depth, audit P14-01). /app must be owned by that
# user because the app creates conversations.db + state files there at runtime.
RUN adduser --system --no-create-home --group app && chown -R app:app /app
USER app

EXPOSE 8000
# Render injects $PORT; bind 0.0.0.0 so the service is reachable.
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
