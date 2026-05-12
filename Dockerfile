# ── Stage 1: Builder ───────────────────────────────────────────
FROM python:3.11-slim AS builder
WORKDIR /app
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Production ────────────────────────────────────────
FROM python:3.11-slim AS production
WORKDIR /app

RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser

COPY --from=builder \
  /usr/local/lib/python3.11/site-packages \
  /usr/local/lib/python3.11/site-packages
COPY --from=builder \
  /usr/local/bin/uvicorn \
  /usr/local/bin/uvicorn

COPY app/main.py .

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_VERSION=1.0.0

USER appuser
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
