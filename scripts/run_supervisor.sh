#!/usr/bin/env bash
# ============================================
# Claw_Rise_bot — Supervisor Startup Script
# Launches health monitor (FastAPI) + bot executor
# Handles restarts, logging, and alerting
# ============================================

set -e

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

# Load .env if present
if [ -f ".env" ]; then
  set -a
  source .env
  set +a
fi

# Ensure directories exist
mkdir -p data/logs generated-cards

# Start health monitor in background
echo "→ Starting health monitor on ${HEALTH_PORT:-8080} ..."
python -m src.health.monitor &
HEALTH_PID=$!

# Start bot executor in foreground (supervisor will restart if it dies)
echo "→ Starting core executor ..."
exec python -m src.bot.executor

# Cleanup on exit
trap 'kill ${HEALTH_PID} 2>/dev/null || true' EXIT
