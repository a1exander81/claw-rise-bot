#!/bin/bash
# ClawForge MTF Bot Watchdog — keeps Freqtrade + Telegram UI alive
# Runs inside OpenClaw container; auto-restarts on crash/hang

set -e

WORKSPACE="/data/.openclaw/workspace"
BOT_DIR="$WORKSPACE/clawmimoto-bot"
LOG_FILE="$BOT_DIR/logs/watchdog.log"
CHECK_INTERVAL=30  # seconds
API_TIMEOUT=3

# Ensure log file exists
touch "$LOG_FILE"
echo "=== Watchdog started at $(date) ===" >> "$LOG_FILE"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

start_freqtrade() {
    log "Starting Freqtrade (strategy: Claw5MHybrid)..."
    cd "$BOT_DIR"
    # Kill any leftover
    pkill -9 -f "freqtrade trade" 2>/dev/null || true
    sleep 2
    nohup python3 -m freqtrade trade \
        --dry-run \
        --config configs/config.json \
        --config configs/config.local.json \
        --strategy Claw5MHybrid \
        > logs/freqtrade.log 2>&1 &
    sleep $API_TIMEOUT
    # Verify API up
    if curl -s --connect-timeout $API_TIMEOUT http://127.0.0.1:8080/api/v1/ping >/dev/null 2>&1; then
        log "✅ Freqtrade started successfully (API responding)"
    else
        log "⚠️  Freqtrade started but API not responding yet — will retry"
    fi
}

start_telegram() {
    log "Starting Telegram UI..."
    cd "$BOT_DIR"
    pkill -9 -f "clawforge.telegram_ui" 2>/dev/null || true
    sleep 1
    nohup python3 -u -m clawforge.telegram_ui > logs/telegram_ui.log 2>&1 &
    sleep 3
    if pgrep -f "clawforge.telegram_ui" >/dev/null 2>&1; then
        log "✅ Telegram UI started (PID $(pgrep -f clawforge.telegram_ui | head -1))"
    else
        log "❌ Telegram UI failed to start"
    fi
}

check_freqtrade() {
    # 1. Process running?
    if ! pgrep -f "freqtrade trade" >/dev/null 2>&1; then
        log "❌ Freqtrade process NOT running — restarting"
        start_freqtrade
        return
    fi
    # 2. API responsive?
    if ! curl -s --connect-timeout $API_TIMEOUT http://127.0.0.1:8080/api/v1/ping >/dev/null 2>&1; then
        log "❌ Freqtrade API not responding — restarting service"
        start_freqtrade
    else
        # log "✅ Freqtrade healthy (API pong)"
        :
    fi
}

check_telegram() {
    if ! pgrep -f "clawforge.telegram_ui" >/dev/null 2>&1; then
        log "❌ Telegram UI NOT running — restarting"
        start_telegram
    else
        # log "✅ Telegram UI healthy"
        :
    fi
}

# Main loop
while true; do
    check_freqtrade
    check_telegram
    sleep $CHECK_INTERVAL
done
