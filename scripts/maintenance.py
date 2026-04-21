#!/usr/bin/env python3
"""
Daily System Maintenance & Health Check
Runs at 20:00 UTC. Performs cleanup, validates strategy/config, reports to admin chat.
"""

import os
import sys
import json
import glob
import shutil
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── Logging Setup ──
LOG_DIR = Path("/data/.openclaw/workspace/clawmimoto-bot/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "maintenance.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# ── Load Config ──
ENV_PATH = Path(__file__).parent.parent / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=True)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "7093901111")
FREQTRADE_API_URL = os.getenv("FREQTRADE_API_URL", "http://127.0.0.1:8080")
FREQTRADE_API_USER = os.getenv("FREQTRADE_API_USER", "admin")
FREQTRADE_API_PASS = os.getenv("FREQTRADE_API_PASS", "admin")

if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not set — aborting")
    sys.exit(1)

# Paths
BOT_DIR = Path(__file__).parent.parent
CONFIG_PATH = BOT_DIR / "configs" / "config.json"
CHANNEL_LOG_PATH = BOT_DIR / "user_data" / "channel_message_log.json"


# ═══════════════════════════════════════════
# STEP 1 — Memory & Data Cleanup
# ═══════════════════════════════════════════
def cleanup_old_files():
    """Remove stale caches, old logs, pycache, expired entries."""
    removed = 0

    # Clear Python pycache directories
    for pycache in BOT_DIR.rglob("__pycache__"):
        try:
            shutil.rmtree(pycache)
            removed += 1
        except Exception as e:
            logger.debug(f"Failed to remove {pycache}: {e}")

    # Compress/remove logs older than 7 days
    cutoff_7d = datetime.now() - timedelta(days=7)
    for log_file in LOG_DIR.glob("*.log"):
        try:
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < cutoff_7d:
                log_file.unlink()
                removed += 1
        except Exception:
            pass

    # Clean expired entries in channel_message_log.json (keep < 7 days)
    if CHANNEL_LOG_PATH.exists():
        try:
            with open(CHANNEL_LOG_PATH, "r", encoding="utf-8") as f:
                logs = json.load(f)
            cutoff_7d_iso = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            cleaned = [e for e in logs if e.get("timestamp", "9999") > cutoff_7d_iso]
            if len(cleaned) < len(logs):
                with open(CHANNEL_LOG_PATH, "w", encoding="utf-8") as f:
                    json.dump(cleaned, f, indent=2)
                logger.info(f"Channel log cleaned: {len(logs) - len(cleaned)} old entries removed")
        except Exception as e:
            logger.error(f"Channel log cleanup failed: {e}")

    logger.info(f"Cleanup step complete — files removed/compressed: {removed}")


# ═══════════════════════════════════════════
# STEP 2 — Health Check (Freqtrade API)
# ═══════════════════════════════════════════
def health_check():
    """Ping Freqtrade and collect status."""
    status = {"api": "down", "trades_count": 0, "balance": 0.0, "strategy": "unknown", "pairs": []}
    try:
        # Ping
        r = requests.get(f"{FREQTRADE_API_URL}/api/v1/ping", auth=(FREQTRADE_API_USER, FREQTRADE_API_PASS), timeout=5)
        if r.status_code == 200:
            status["api"] = "ok"
            data = r.json()
            # Get status (open trades)
            r2 = requests.get(f"{FREQTRADE_API_URL}/api/v1/status", auth=(FREQTRADE_API_USER, FREQTRADE_API_PASS), timeout=5)
            if r2.status_code == 200:
                trades = r2.json()
                status["trades_count"] = len(trades)
                if trades:
                    status["pairs"] = list({t.get("pair", "?") for t in trades})

            # Get balance
            r3 = requests.get(f"{FREQTRADE_API_URL}/api/v1/balance", auth=(FREQTRADE_API_USER, FREQTRADE_API_PASS), timeout=5)
            if r3.status_code == 200:
                bal_data = r3.json()
                # Balance: { "total": 1234.56, ... } — 'total' is float
                status["balance"] = bal_data.get("total", 0.0) if isinstance(bal_data, dict) else 0.0
            else:
                status["balance"] = 0.0

            # Get strategy name from config
            if CONFIG_PATH.exists():
                try:
                    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    status["strategy"] = cfg.get("strategy", "unknown")
                except Exception:
                    pass
        else:
            logger.warning(f"Freqtrade ping failed: {r.status_code}")
    except Exception as e:
        logger.error(f"Health check error: {e}")

    return status


# ═══════════════════════════════════════════
# STEP 3 — Strategy Validation
# ═══════════════════════════════════════════
def validate_strategy():
    """Verify key strategy parameters are loaded."""
    checks = {"custom_stoploss": False, "minimal_roi": False, "trailing_stop": False, "pair_count": 0}
    try:
        r = requests.get(f"{FREQTRADE_API_URL}/api/v1/strategy", auth=(FREQTRADE_API_USER, FREQTRADE_API_PASS), timeout=5)
        if r.status_code == 200:
            strat = r.json()
            checks["custom_stoploss"] = strat.get("custom_stoploss") is not None
            checks["minimal_roi"] = strat.get("minimal_roi") is not None
            checks["trailing_stop"] = strat.get("trailing_stop") is not None
            # Pair whitelist length
            pairs = strat.get("pair_whitelist", [])
            checks["pair_count"] = len(pairs) if isinstance(pairs, list) else 0
    except Exception as e:
        logger.error(f"Strategy validation failed: {e}")
    return checks


# ═══════════════════════════════════════════
# STEP 4 — Channel Message Log Dedup
# ═══════════════════════════════════════════
def dedup_channel_log():
    """Remove duplicate message_ids from channel log."""
    if not CHANNEL_LOG_PATH.exists():
        return 0
    try:
        with open(CHANNEL_LOG_PATH, "r", encoding="utf-8") as f:
            logs = json.load(f)
        seen = set()
        deduped = []
        dupes = 0
        for entry in logs:
            mid = entry.get("message_id")
            if mid is None or mid in seen:
                dupes += 1
                continue
            seen.add(mid)
            deduped.append(entry)
        if dupes > 0:
            with open(CHANNEL_LOG_PATH, "w", encoding="utf-8") as f:
                json.dump(deduped, f, indent=2)
        return dupes
    except Exception as e:
        logger.error(f"Dedup failed: {e}")
        return 0


# ═══════════════════════════════════════════
# STEP 5 — Admin Report
# ═══════════════════════════════════════════
def send_admin_report(health: dict, strat_checks: dict, dupes_removed: int):
    """Send formatted maintenance summary to admin chat."""
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    status_emoji = "✅" if health["api"] == "ok" else "❌"

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"🔧 SYSTEM MAINTENANCE — {now_utc}",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"{status_emoji} Freqtrade API: {health['api'].upper()}",
        f"💰 Balance: {health['balance']:,.2f} USDT",
        f"📊 Open Trades: {health['trades_count']}",
        f"🧠 Strategy: {health['strategy']}",
        f"🔗 Active Pairs: {strat_checks['pair_count']}",
        f"🧹 Channel duplicates cleaned: {dupes_removed}",
        "",
        "✅ Checks:",
        f"  {'✓' if strat_checks['custom_stoploss'] else '✗'} custom_stoploss",
        f"  {'✓' if strat_checks['minimal_roi'] else '✗'} minimal_roi",
        f"  {'✓' if strat_checks['trailing_stop'] else '✗'} trailing_stop",
        "",
        "🤖 System ready for next session",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]
    message = "\n".join(lines)

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            logger.info("Maintenance report sent to admin chat")
        else:
            logger.error(f"Failed to send report: {r.status_code} {r.text[:200]}")
    except Exception as e:
        logger.error(f"Exception sending report: {e}")


# ═══════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════
def main():
    logger.info("Starting daily maintenance run")
    start_time = datetime.now(timezone.utc)

    # STEP 1 — Cleanup
    cleanup_old_files()

    # STEP 2 — Health check
    health = health_check()
    logger.info(f"Health check — API: {health['api']}, Trades: {health['trades_count']}, Balance: {health['balance']}")

    # STEP 3 — Strategy validation
    strat = validate_strategy()
    logger.info(f"Strategy validation — pairs: {strat['pair_count']}, stops: {strat['custom_stoploss']}/{strat['trailing_stop']}")

    # STEP 4 — Dedup channel log
    dupes = dedup_channel_log()
    if dupes:
        logger.info(f"Deduplicated channel log — removed {dupes} duplicate entries")

    # STEP 5 — Admin report
    send_admin_report(health, strat, dupes)

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info(f"Maintenance complete in {duration:.1f}s")


if __name__ == "__main__":
    main()
