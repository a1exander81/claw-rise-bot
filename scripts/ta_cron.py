#!/usr/bin/env python3
"""
4-Hour Technical Analysis Cron Job
Fetches Binance 4H klines for BTC/USDT, ETH/USDT, SOL/USDT, BNB/USDT
Generates support/resistance levels and sends formatted updates to Telegram.
"""

import os
import sys
import json
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
        logging.FileHandler(LOG_DIR / "ta_cron.log", encoding="utf-8"),
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
if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not set in .env — aborting")
    sys.exit(1)

# Binance public endpoint (no key needed)
BINANCE_BASE = "https://api.binance.com/api/v3"
PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
INTERVAL = "4h"
LIMIT = 50  # fetch last 50 candles; we use last 10 for S/R


def fetch_klines(symbol: str) -> list | None:
    """Fetch OHLCV klines from Binance. Returns list of [open, high, low, close, ...]."""
    url = f"{BINANCE_BASE}/klines"
    params = {"symbol": symbol, "interval": INTERVAL, "limit": LIMIT}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        # Binance returns list of lists; indices: 0=open_time,1=open,2=high,3=low,4=close,...
        return [[float(c[1]), float(c[2]), float(c[3]), float(c[4])] for c in data]
    except Exception as e:
        logger.warning(f"Binance fetch failed for {symbol}: {e}")
        return None


def calculate_sr(klines: list) -> tuple[float, float]:
    """Return (current_close, resistance, support) based on last 10 candles."""
    recent = klines[-10:]  # last 10 candles
    closes = [k[3] for k in klines]  # close prices
    current_price = closes[-1]
    resistance = max(k[1] for k in recent)  # highest high
    support = min(k[2] for k in recent)      # lowest low
    return current_price, resistance, support


def generate_narrative(symbol: str, klines: list, current: float, res: float, sup: float) -> str:
    """Create 2-3 sentence TA narrative."""
    # Trend: compare price to 10-candle average close
    avg_close = sum(k[3] for k in klines[-10:]) / 10
    if current > avg_close * 1.005:
        trend = "trending up"
    elif current < avg_close * 0.995:
        trend = "trending down"
    else:
        trend = "ranging"

    # Price position relative to S/R
    distance_res = (res - current) / current * 100
    distance_sup = (current - sup) / current * 100

    # Simple volume check not available from basic klines; skip
    narrative = (
        f"{symbol.replace('USDT', '/USDT')} is {trend} on the 4H timeframe. "
        f"Price ${current:,.2f} is {distance_res:.1f}% below resistance (${res:,.2f}) "
        f"and {distance_sup:.1f}% above support (${sup:,.2f})."
    )
    return narrative


def send_telegram_message(token: str, chat_id: str, text: str) -> bool:
    """Send formatted message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False


def main():
    logger.info("Starting 4H TA update run")
    now_utc = datetime.now(timezone.utc)
    time_str = now_utc.strftime("%Y-%m-%d %H:%M UTC")

    # Header
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"📊 4H TA UPDATE — {time_str}",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for symbol in PAIRS:
        klines = fetch_klines(symbol)
        if not klines or len(klines) < 10:
            logger.warning(f"Skipping {symbol}: insufficient data")
            lines.append(f"❌ {symbol.replace('USDT', '/USDT')} — data unavailable")
            continue

        current, resistance, support = calculate_sr(klines)
        narrative = generate_narrative(symbol, klines, current, resistance, support)

        lines.append(f"🔵 {symbol.replace('USDT', '/USDT')}")
        lines.append(narrative)
        lines.append(f"💰 Price: ${current:,.2f}")
        lines.append(f"🔴 Resistance: ${resistance:,.2f}")
        lines.append(f"🟢 Support: ${support:,.2f}")
        lines.append("")  # blank line between pairs

    # Footer
    lines.extend([
        "━━━━━━━━━━━━━━━━━━━━━━",
        "⚡ Powered by Clawmimoto Analytics",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ])

    message = "\n".join(lines)
    logger.info(f"Sending TA update to chat {TELEGRAM_CHAT_ID}")
    # Send and capture message_id
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        result = r.json()
        msg_id = result.get("result", {}).get("message_id")
        if msg_id:
            # Log to channel_message_log.json (append)
            log_path = Path(__file__).parent.parent / "user_data" / "channel_message_log.json"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "message_id": msg_id,
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "chat_id": TELEGRAM_CHAT_ID,
                "type": "ta_update",
            }
            logs = []
            if log_path.exists():
                try:
                    with open(log_path, "r", encoding="utf-8") as lf:
                        logs = json.load(lf)
                except Exception:
                    logs = []
            logs.append(entry)
            with open(log_path, "w", encoding="utf-8") as lf:
                json.dump(logs, lf, indent=2, ensure_ascii=False)
            logger.info(f"Logged TA message ID {msg_id} to channel_message_log.json")
        logger.info("Telegram message sent successfully")
        return True
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False


if __name__ == "__main__":
    main()
