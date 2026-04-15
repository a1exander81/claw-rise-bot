# ============================================
# Claw_Rise_bot — Dockerfile (single-stage, explicit copy)
# ============================================

FROM python:3.11-slim

WORKDIR /app

# System deps for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libssl-dev \
    libffi-dev \
    libatlas-base-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements first (for layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code explicitly
COPY src ./src
COPY config ./config
COPY web ./web
COPY scripts ./scripts
COPY data ./data
COPY logs ./logs
COPY generated-cards ./generated-cards
COPY *.md *.yaml *.yml ./

# Ensure runtime dirs exist (if not already)
RUN mkdir -p data/logs data/candles generated-cards logs

# Expose health endpoint
EXPOSE 8080

# Default command (overridden by docker-compose if needed)
CMD ["python", "-m", "src.bot.executor"]
