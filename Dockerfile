FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONPATH=/app/backend \
    ACCD_ROOT=/app \
    PORT=7860

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /app/requirements.txt

COPY . /app

# HF Spaces default 7860; Render sets $PORT
EXPOSE 7860

CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860} --log-level info
