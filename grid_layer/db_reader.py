# grid_layer/db_reader.py
"""Read-only access to passivbot's SQLite database."""
import sqlite3
import os
from typing import Optional

PASSIVBOT_DB = os.environ.get("PASSIVBOT_DB", "./passivbot/data/passivbot.db")

def _connect(readonly: bool = True) -> sqlite3.Connection:
    if readonly:
        uri = f"file:{PASSIVBOT_DB}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    else:
        conn = sqlite3.connect(PASSIVBOT_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def get_grid_positions() -> list:
    try:
        conn = _connect()
        cur = conn.cursor()
        cur.execute("SELECT * FROM positions WHERE is_open = 1 LIMIT 10;")
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []

def get_grid_trades(limit: int = 10) -> list:
    try:
        conn = _connect()
        cur = conn.cursor()
        cur.execute("SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?;", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []

def get_grid_pnl() -> Optional[dict]:
    try:
        conn = _connect()
        cur = conn.cursor()
        cur.execute("SELECT SUM(pnl) as total_pnl, COUNT(*) as total_trades FROM trades;")
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None
