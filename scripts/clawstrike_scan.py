#!/usr/bin/env python3
"""
ClawStrike Auto-Scanner — Standalone cron job
Runs every 5 minutes during London (07:45-09:00 UTC) and NY (12:45-14:00 UTC) windows.
Checks BTC/USDT, ETH/USDT, SOL/USDT and fires if all 8 conditions met.
Max 1 trade per day enforced via clawstrike_log.json.
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime, timezone
from pathlib import Path

# ── Load .env if present ──
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass  # dotenv optional

# ── Project root on PYTHONPATH ──
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── Config ──
FREQTRADE_API_URL = os.getenv("FREQTRADE_API_URL", "http://127.0.0.1:8080")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Windows (UTC): London 07:45-09:00, NY 12:45-14:00, Weekdays only
LONDON_WINDOW = (7, 9)      # 07:45 – 09:00 UTC
NY_WINDOW = (12, 14)        # 12:45 – 14:00 UTC

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ── Freqtrade API helpers ──
def api_get(endpoint: str):
    try:
        r = requests.get(f"{FREQTRADE_API_URL}{endpoint}", timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        logger.error(f"GET {endpoint} failed: {e}")
        return None

def api_post(endpoint: str, payload: dict):
    try:
        r = requests.post(f"{FREQTRADE_API_URL}{endpoint}", json=payload, timeout=10)
        if r.status_code == 200:
            return True, r.json()
        return False, r.text
    except Exception as e:
        logger.error(f"POST {endpoint} failed: {e}")
        return False, str(e)

# ── Import ClawStrike logic from telegram_ui ──
try:
    from clawforge.telegram_ui import check_clawstrike_conditions, execute_clawstrike
except Exception as e:
    logger.error(f"Failed to import ClawStrike functions: {e}")
    sys.exit(1)

# ── Main ──
def main():
    now = datetime.now(timezone.utc)
    hour = now.hour
    weekday = now.weekday()  # 0=Mon, 6=Sun

    # Weekend check
    if weekday >= 5:
        logger.info("Weekend — ClawStrike scan skipped")
        return 0

    # Window check
    in_london = LONDON_WINDOW[0] <= hour < LONDON_WINDOW[1]
    in_ny = NY_WINDOW[0] <= hour < NY_WINDOW[1]
    if not (in_london or in_ny):
        logger.info(f"Outside trading windows (hour {hour}) — exiting")
        return 0

    logger.info(f"ClawStrike scan start — window={'LONDON' if in_london else 'NY'}")

    pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    chat_id = int(TELEGRAM_CHAT_ID) if TELEGRAM_CHAT_ID else None

    for pair in pairs:
        logger.info(f"Checking {pair}...")
        try:
            eligible, reason, score = check_clawstrike_conditions(pair, chat_id)
            if eligible:
                logger.info(f"✅ ELIGIBLE: {reason} — executing ClawStrike")
                execute_clawstrike(pair, score)
                # Only one per day; stop after first execution
                break
            else:
                logger.debug(f"❌ Not eligible: {reason}")
        except Exception as e:
            logger.error(f"Error processing {pair}: {e}", exc_info=True)

    logger.info("ClawStrike scan complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())
