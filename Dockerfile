# Multi-stage Docker build for ClawForge MTF Bot
FROM python:3.13-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    libffi-dev \
    libssl-dev \
    pkg-config \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.13-slim

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY clawforge/ ./clawforge/
COPY configs/ ./configs/
COPY strategies/ ./strategies/

# Create directories for data
RUN mkdir -p /app/user_data/logs \
    /app/user_data/strategies \
    /app/user_data/data \
    /app/generated/cards \
    /app/generated-cards

# Environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Singapore

# Health check for Freqtrade API
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://127.0.0.1:8080/api/v1/ping || exit 1

# Default: run both services via supervisord-like script
# But we'll use docker-compose to run them as separate services
