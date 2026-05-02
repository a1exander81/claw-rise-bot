# config/sessions.py
from datetime import time, timezone

TRADING_SESSIONS = {
    "pre_london": {
        "name": "Pre-London",
        "emoji": "🌅",
        "gmt_start": time(6, 0),
        "gmt_end": time(8, 0),
        "volatility_level": "rising",
        "claw_settings": {
            "max_trades_per_session": 1,
            "risk_per_trade_pct": 0.5,
            "min_volume_threshold": 0.5,
        },
        "grid_settings": {
            "grid_spacing_factor": 0.8,
            "tp_markup_pct": 0.08,
            "max_wallet_exposure_pct": 10,
        },
    },
    "london": {
        "name": "London",
        "emoji": "🇬🇧",
        "gmt_start": time(8, 0),
        "gmt_end": time(16, 0),
        "volatility_level": "high",
        "claw_settings": {
            "max_trades_per_session": 3,
            "risk_per_trade_pct": 1.0,
            "min_volume_threshold": 0.7,
        },
        "grid_settings": {
            "grid_spacing_factor": 1.2,
            "tp_markup_pct": 0.15,
            "max_wallet_exposure_pct": 20,
        },
    },
    "ny": {
        "name": "New York",
        "emoji": "🇺🇸",
        "gmt_start": time(13, 0),
        "gmt_end": time(22, 0),
        "volatility_level": "very_high",
        "claw_settings": {
            "max_trades_per_session": 4,
            "risk_per_trade_pct": 1.0,
            "min_volume_threshold": 0.8,
        },
        "grid_settings": {
            "grid_spacing_factor": 1.5,
            "tp_markup_pct": 0.20,
            "max_wallet_exposure_pct": 25,
        },
    },
}

def is_overlap() -> bool:
    from datetime import datetime
    now = datetime.now(timezone.utc).time()
    return time(13, 0) <= now < time(16, 0)

def get_active_sessions() -> list[str]:
    from datetime import datetime
    now = datetime.now(timezone.utc).time()
    active = []
    for key, sess in TRADING_SESSIONS.items():
        if sess["gmt_start"] <= now < sess["gmt_end"]:
            active.append(key)
    return active