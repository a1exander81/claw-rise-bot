#!/usr/bin/env python3
"""
Channel Message Auto-Cleanup
Deletes messages older than 48 hours from @RightclawTrade channel.
Requires bot to be ADMIN with "Delete messages" permission.
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
        logging.FileHandler(LOG_DIR / "channel_cleanup.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# ── Load Config ──
ENV_PATH = Path(__file__).parent.parent / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=True)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not set in .env — aborting")
    sys.exit(1)

# Channel configuration
CHANNEL_USERNAME = "@RightclawTrade"  # or channel ID if known
MESSAGE_LOG_PATH = Path(__file__).parent.parent / "user_data" / "channel_message_log.json"
MESSAGE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# Telegram API
TG_API = "https://api.telegram.org/bot{token}/deleteMessage"


def load_message_log() -> list:
    """Load tracked message IDs from JSON log."""
    if not MESSAGE_LOG_PATH.exists():
        return []
    try:
        with open(MESSAGE_LOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        logger.warning("channel_message_log.json has invalid format — resetting")
        return []
    except Exception as e:
        logger.error(f"Failed to read message log: {e}")
        return []


def save_message_log(log_data: list) -> None:
    """Write message log back to disk."""
    try:
        with open(MESSAGE_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save message log: {e}")


def delete_message(token: str, chat_id: str, message_id: int) -> bool:
    """Delete a single message via Telegram Bot API."""
    url = TG_API.format(token=token)
    payload = {"chat_id": chat_id, "message_id": message_id}
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            return True
        elif r.status_code == 400 and "message to delete not found" in r.text.lower():
            logger.info(f"Message {message_id} already deleted — skipping")
            return True  # treat as success
        else:
            logger.warning(f"Delete failed for msg {message_id}: {r.status_code} {r.text[:100]}")
            return False
    except Exception as e:
        logger.error(f"Exception deleting msg {message_id}: {e}")
        return False


def main():
    logger.info("Starting channel cleanup run")
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=48)

    # Load message log
    message_log = load_message_log()
    logger.info(f"Loaded {len(message_log)} tracked messages")

    # Parse timestamps and filter old messages
    to_delete = []
    to_keep = []

    for entry in message_log:
        try:
            ts = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
            if ts < cutoff:
                to_delete.append(entry)
            else:
                to_keep.append(entry)
        except Exception:
            logger.warning(f"Invalid timestamp in entry: {entry}")
            to_keep.append(entry)  # keep malformed entries

    logger.info(f"Found {len(to_delete)} messages older than 48h to delete")

    # Delete messages (rate-limited: 1 sec between deletes)
    deleted_count = 0
    for entry in to_delete:
        msg_id = entry["message_id"]
        success = delete_message(TELEGRAM_BOT_TOKEN, CHANNEL_USERNAME, msg_id)
        if success:
            deleted_count += 1
            # Wait 1 second to respect rate limits
            import time
            time.sleep(1)
        # else: keep entry in log for retry later (do not add to to_keep)

    # Update log: remove successfully deleted entries
    new_log = to_keep
    save_message_log(new_log)

    logger.info(f"Cleanup complete — deleted {deleted_count}/{len(to_delete)} messages")
    logger.info(f"Remaining tracked messages: {len(new_log)}")


if __name__ == "__main__":
    main()
