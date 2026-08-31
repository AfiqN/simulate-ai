# syntax=docker/dockerfile:1.7
FROM node:22-alpine AS frontend-builder
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000
WORKDIR /app

RUN addgroup --system simulateai && adduser --system --ingroup simulateai simulateai
COPY requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt
COPY --chown=simulateai:simulateai . .
COPY --from=frontend-builder --chown=simulateai:simulateai /build/static/dist ./static/dist
RUN mkdir -p /app/data /app/tests/runs && chown -R simulateai:simulateai /app/data /app/tests/runs

USER simulateai
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/api/readiness', timeout=3)"
CMD ["sh", "-c", "exec uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
