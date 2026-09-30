FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# System deps: build tools for tree-sitter / numpy wheels, git for LSP, curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Requirements first (layer caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /app/requirements.txt

# App source
COPY . /app

# Give the backend the backend/ dir on PYTHONPATH
ENV PYTHONPATH=/app/backend
ENV ACCD_ROOT=/app

EXPOSE 7860

# HF Spaces routes to port 7860
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860", "--log-level", "info"]
