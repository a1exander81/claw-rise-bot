#!/usr/bin/env python3
"""Replace BingX references with Bybit in telegram_ui.py"""

import re

path = "/data/.openclaw/workspace/clawmimoto-bot/clawforge/telegram_ui.py"

with open(path, "r") as f:
    content = f.read()

# 1. Replace env var loading section: add BYBIT reads
content = content.replace(
    "BINGX_API_KEY = os.getenv(\"BINGX_API_KEY\")\nBINGX_API_SECRET = os.getenv(\"BINGX_API_SECRET\")",
    "BINGX_API_KEY = os.getenv(\"BINGX_API_KEY\")\nBINGX_API_SECRET = os.getenv(\"BINGX_API_SECRET\")\nBYBIT_API_KEY = os.getenv(\"BYBIT_API_KEY\")\nBYBIT_API_SECRET = os.getenv(\"BYBIT_API_SECRET\")"
)

# 2. Replace comment
content = content.replace("# ── BingX API ──", "# ── Bybit API (v5) ──")

# 3. Replace bingx_signed_request with bybit_signed_request (full function)
old_func = '''def bingx_signed_request(method, endpoint, params=None):
    if not BINGX_API_KEY or not BINGX_API_SECRET:
        return None
    base_url = "https://open-api.bingx.com"
    url = f"{base_url}{endpoint}"
    if params:
        sorted_params = sorted(params.items())
        query = '&'.join([f"{k}={v}" for k, v in sorted_params])
        signature = hmac.new(BINGX_API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
        url += f"?{query}&signature={signature}"
    headers = {"X-BX-APIKEY": BINGX_API_KEY, "Content-Type": "application/json"}
    try:
        r = requests.request(method, url, headers=headers, timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        logger.error(f"BingX API error: {e}")
        return None'''

new_func = '''def bybit_signed_request(method: str, endpoint: str, params: dict = None, body: dict = None):
    if not BYBIT_API_KEY or not BYBIT_API_SECRET:
        return None
    import time
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"
    base_url = "https://api.bybit.com"
    url = f"{base_url}{endpoint}"
    if params:
        sorted_params = sorted(params.items())
        query = '&'.join([f"{k}={v}" for k, v in sorted_params])
        url += f"?{query}"
    body_str = ""
    if body and method.upper() == "POST":
        import json
        body_str = json.dumps(body, separators=(',', ':'), sort_keys=True)
    sign_str = f"{timestamp}{method.upper()}{recv_window}{body_str}"
    signature = hmac.new(BYBIT_API_SECRET.encode(), sign_str.encode(), hashlib.sha256).hexdigest()
    headers = {
        "X-BAPI-API-KEY": BYBIT_API_KEY,
        "X-BAPI-SIGN": signature,
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-RECV-WINDOW": recv_window,
        "Content-Type": "application/json"
    }
    try:
        r = requests.request(method, url, headers=headers, data=body_str if method.upper() == "POST" else None, timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        logger.error(f"Bybit API error: {e}")
        return None'''

content = content.replace(old_func, new_func)

# 4. Replace get_bingx_hot_pairs
old_hot = '''def get_bingx_hot_pairs(limit=5):
    """Fetch top hot pairs from BingX ticker — USDT-margined only."""
    try:
        data = bingx_signed_request("GET", "/openApi/swap/v2/quote/ticker", timeout=5)
        if data and "data" in data:
            pairs = []
            for item in data["data"]:
                symbol = item.get("symbol", "").upper()
                # BingX uses BTC-USDT format; convert to BTC/USDT
                symbol = symbol.replace("-", "/")
                # **USDT-margined perpetuals only**
                if symbol.endswith("/USDT"):
                    pairs.append(symbol)
                if len(pairs) >= limit:
                    break
            logger.info(f"BingX USDT hot pairs: {pairs}")
            if pairs:
                return pairs
    except Exception as e:
        logger.debug(f"BingX hot pairs error: {e}")
    # Fallback to Binance 24hr gainers (USDT pairs only)
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=5)
        if r.status_code == 200:
            data = r.json()
            stable = ["USDT", "USDC", "BUSD", "DAI"]
            # Only USDT pairs, exclude stablecoins
            filtered = [d for d in data if d.get("symbol", "").endswith("USDT") and not any(s in d.get("symbol", "") for s in stable)]
            filtered.sort(key=lambda x: float(x.get("priceChangePercent", 0)), reverse=True)
            pairs = []
            for d in filtered:
                sym = d['symbol']
                if len(sym) >= 4 and sym.endswith("USDT"):
                    base = sym[:-4]
                    pairs.append(f"{base}/USDT")
                if len(pairs) >= limit:
                    break
            logger.info(f"Binance fallback USDT pairs: {pairs}")
            if pairs:
                return pairs
    except Exception as e:
        logger.debug(f"Binance fallback error: {e}")
    # Ultimate fallback — USDT only
    fallback = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"][:limit]
    logger.warning("All hot pair sources failed, using USDT-only hardcoded list")
    return fallback'''

new_hot = '''def get_bybit_hot_pairs(limit: int = 5) -> list:
    """Fetch top volatile USDT perpetual pairs from Bybit ticker."""
    try:
        data = bybit_signed_request("GET", "/v5/market/tickers", params={"category": "linear"}, timeout=5)
        if data and data.get("retCode") == 0:
            items = data.get("result", {}).get("list", [])
            pairs = []
            for item in items:
                symbol = item.get("symbol", "")
                if symbol.endswith("USDT"):
                    base = symbol[:-4]
                    pairs.append(f"{base}/USDT")
                if len(pairs) >= limit:
                    break
            logger.info(f"Bybit hot USDT pairs: {pairs}")
            if pairs:
                return pairs
    except Exception as e:
        logger.debug(f"Bybit hot pairs error: {e}")
    fallback = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"][:limit]
    logger.warning("Bybit hot pairs fetch failed, using fallback USDT list")
    return fallback'''

content = content.replace(old_hot, new_hot)

# 5. Replace get_bingx_klines
old_klines = '''def get_bingx_klines(symbol, interval="5m", limit=50):
    """Fetch klines from BingX with Binance fallback."""
    # Try BingX first
    try:
        data = bingx_signed_request("GET", "/openApi/swap/v2/quote/klines", {"symbol": symbol, "interval": interval, "limit": str(limit)}, timeout=5)
        if data and "data" in data and len(data["data"]) >= limit:
            logger.info(f"Data source: BingX klines for {symbol}")
            return data
    except Exception as e:
        logger.debug(f"BingX klines error: {e}")
    # Fallback to Binance
    try:
        binance_symbol = symbol.replace("/", "")
        url = f"https://api.binance.com/api/v3/klines?symbol={binance_symbol}&interval={interval}&limit={limit}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            raw = r.json()
            candles = []
            for c in raw:
                candles.append({
                    "open": c[1], "high": c[2], "low": c[3], "close": c[4], "volume": c[5]
                })
            logger.info(f"Binance klines fallback for {symbol} ({len(candles)} candles)")
            return {"data": candles}
    except Exception as e:
        logger.debug(f"Binance klines error: {e}")
    return None'''

new_klines = '''def get_bybit_klines(symbol: str, interval: str = "5m", limit: int = 50):
    """Fetch klines from Bybit. symbol format: BTC/USDT (converted to BTCUSDT)."""
    try:
        bybit_symbol = symbol.replace("/", "").upper()
        data = bybit_signed_request(
            "GET",
            "/v5/market/kline",
            params={"category": "linear", "symbol": bybit_symbol, "interval": interval, "limit": str(limit)},
            timeout=5
        )
        if data and data.get("retCode") == 0:
            klines = data.get("result", {}).get("list", [])
            if klines:
                logger.info(f"Bybit klines for {symbol}: {len(klines)} candles")
                candles = []
                for k in klines:
                    candles.append({"open": k[1], "high": k[2], "low": k[3], "close": k[4], "volume": k[5]})
                return {"data": candles}
    except Exception as e:
        logger.debug(f"Bybit klines error for {symbol}: {e}")
    return None'''

content = content.replace(old_klines, new_klines)

# 6. Replace is_pair_valid_on_bingx and is_pair_valid_for_user
old_valid = '''def is_pair_valid_on_bingx(pair: str) -> bool:
    """Check if pair exists as a perpetual swap on BingX (USDT-margined only).
    Binance fallback removed — it validates spot markets, not futures.
    """
    # Only USDT-margined futures are supported in this bot
    if not pair.endswith("/USDT"):
        logger.debug(f"Pair {pair} rejected: non-USDT quote (futures mode)")
        return False
    try:
        symbol = pair.replace("/", "-").upper()
        ticker = bingx_signed_request("GET", "/openApi/swap/v2/quote/ticker", {"symbol": symbol})
        if ticker and "data" in ticker:
            data = ticker["data"]
            price = float(data.get("lastPrice", 0))
            if price > 0:
                return True
    except Exception as e:
        logger.debug(f"BingX validation error for {pair}: {e}")
    return False

def is_pair_valid_for_user(pair: str, user_id: int) -> bool:
    """Admin bypass: admins can use any pair without API validation."""
    if is_admin(user_id):
        return True
    return is_pair_valid_on_bingx(pair)'''

new_valid = '''def is_pair_valid_on_bybit(pair: str) -> bool:
    """Check if pair exists as a perpetual swap on Bybit (USDT-margined linear)."""
    if not pair.endswith("/USDT"):
        logger.debug(f"Pair {pair} rejected: non-USDT quote (futures mode)")
        return False
    try:
        base = pair.split("/")[0]
        bybit_symbol = f"{base}USDT"
        data = bybit_signed_request("GET", "/v5/market/tickers", params={"category": "linear", "symbol": bybit_symbol}, timeout=5)
        if data and data.get("retCode") == 0:
            result = data.get("result", {})
            list_data = result.get("list", [])
            if list_data and len(list_data) > 0:
                price = float(list_data[0].get("lastPrice", 0))
                if price > 0:
                    return True
    except Exception as e:
        logger.debug(f"Bybit validation error for {pair}: {e}")
    return False

def is_pair_valid_for_user(pair: str, user_id: int) -> bool:
    """Admin bypass: admins can use any pair without API validation."""
    if is_admin(user_id):
        return True
    return is_pair_valid_on_bybit(pair)'''

content = content.replace(old_valid, new_valid)

# 7. Replace remaining function names in body
content = content.replace("get_bingx_hot_pairs", "get_bybit_hot_pairs")
content = content.replace("get_bingx_klines", "get_bybit_klines")
content = content.replace("is_pair_valid_on_bingx", "is_pair_valid_on_bybit")
content = content.replace("validate_pair_on_bingx", "validate_pair_on_bybit")
content = content.replace("extract_pair_from_bingx_url", "extract_pair_from_bybit_url")
content = content.replace("bingx_signed_request", "bybit_signed_request")

# 8. Update URL checks
content = content.replace('"bingx.com"', '"bybit.com"')
content = content.replace("bingx.com", "bybit.com")

# 9. In analyze_pair, change get_bingx_klines call (already replaced above but ensure)
content = content.replace('klines_data = get_bingx_klines(symbol, interval="5m", limit=50)', 'klines_data = get_bybit_klines(symbol, interval="5m", limit=50)')

# 10. In get_balance, replace BINGX check and endpoint
old_balance = '''    # Real: from BingX
    real = None
    if BINGX_API_KEY and BINGX_API_SECRET:
        data = bingx_signed_request("GET", "/openApi/swap/v2/account/balance")
        if data and "data" in data:
            for asset in data["data"]:
                if asset.get("asset") == "USDT":
                    real = float(asset.get("available", 0))'''

new_balance = '''    # Real: from Bybit
    real = None
    if BYBIT_API_KEY and BYBIT_API_SECRET:
        data = bybit_signed_request("GET", "/v5/account/wallet-balance", params={"accountType": "CONTRACT"})
        if data and data.get("retCode") == 0:
            for asset in data.get("result", {}).get("list", [{}])[0].get("coin", []):
                if asset.get("coin") == "USDT":
                    real = float(asset.get("availableToWithdraw", 0) or 0)'''

content = content.replace(old_balance, new_balance)

# 11. Replace extract_pair_from_bingx_url function body
old_extract = '''def extract_pair_from_bingx_url(url):
    """Extract pair from BingX perpetual URL.
    Example: https://bingx.com/en/perpetual/GENIUS-USDT -> GENIUS/USDT
    """
    import re
    match = re.search(r"perpetual/([A-Z0-9-]+)", url, re.IGNORECASE)
    if match:
        symbol = match.group(1).replace("-", "/")
        return symbol.upper()
    return None'''

new_extract = '''def extract_pair_from_bybit_url(url: str) -> str:
    """Extract pair from Bybit perpetual URL.
    Example: https://www.bybit.com/trading/linear/BTCUSDT -> BTC/USDT
    """
    import re
    match = re.search(r"linear/([A-Z0-9]+)", url, re.IGNORECASE)
    if match:
        symbol = match.group(1).upper()
        if symbol.endswith("USDT"):
            base = symbol[:-4]
            return f"{base}/USDT"
    return None'''

content = content.replace(old_extract, new_extract)

# Write back
with open(path, "w") as f:
    f.write(content)

print("✅ telegram_ui.py converted from BingX to Bybit")
