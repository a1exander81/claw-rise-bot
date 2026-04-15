# ============================================
# Claw_Rise_bot — WebUI Dockerfile
# Simple Flask + Jinja2 static dashboard
# ============================================

FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

# Copy source (data is mounted via docker-compose at runtime)
COPY web ./web
COPY src ./src
COPY config ./config

EXPOSE 8000

CMD ["python", "-m", "web.server"]
