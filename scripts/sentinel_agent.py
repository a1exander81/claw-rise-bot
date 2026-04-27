"""
╔═══════════════════════════════════════════════════════╗
║           C L A W T C H E R  S E N T I N E L         ║
║   Predictive Macro Intelligence Agent                 ║
║   Layer 0-4: Data → Signals → BED → Score → Output   ║
║   Built on OpenClaw Foundation                        ║
╚═══════════════════════════════════════════════════════╝

Admin-exclusive feature. Confluence tool for session trading.
"""

import os, json, time, re, math, logging
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request, urllib.parse, ssl
import xml.etree.ElementTree as ET

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sentinel")

# ── CONFIG ──
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))

SSL_CTX = ssl.create_default_context()

# ══════════════════════════════════════════════════════
# LAYER 0: DATA INGESTION
# ══════════════════════════════════════════════════════

RSS_FEEDS = [
    ("CoinTelegraph",   "https://cointelegraph.com/rss"),
    ("CoinDesk",        "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Decrypt",         "https://decrypt.co/feed"),
    ("Bitcoin Magazine","https://bitcoinmagazine.com/feed"),
    ("Crypto.news",     "https://crypto.news/feed/"),
    ("CoinTelegraph Markets", "https://cointelegraph.com/rss/tag/markets"),
]

# Macro keywords with impact scores
BULLISH_TIER1 = [
    "rate cut", "pivot", "etf approved", "etf inflows", "whale accumulation",
    "institutional buying", "btc conference", "bitcoin conference", "halving",
    "cpi lower", "inflation falls", "fed pause", "rate hold dovish",
    "sec approves", "spot etf", "strategic reserve", "treasury buys bitcoin"
]
BULLISH_TIER2 = [
    "etf inflow", "institutional", "adoption", "accumulation", "breakout",
    "ath", "all time high", "record high", "rally", "surge", "moon",
    "bullish", "buy", "long", "support holds", "recovery", "rebound"
]
BULLISH_TIER3 = [
    "bitcoin", "crypto rises", "gains", "positive", "optimistic", "upgrade"
]

BEARISH_TIER1 = [
    "rate hike", "hawkish", "etf rejected", "etf outflows", "exchange hack",
    "sec crackdown", "doj charges", "cpi higher", "inflation rises",
    "bank collapse", "whale dump", "massive sell", "liquidation cascade",
    "regulatory ban", "china bans"
]
BEARISH_TIER2 = [
    "etf outflow", "sell off", "crash", "dump", "bearish", "correction",
    "resistance", "rejection", "weakness", "fear", "uncertainty",
    "regulatory", "lawsuit", "investigation", "ban"
]
BEARISH_TIER3 = [
    "falls", "drops", "declines", "negative", "concern", "worry"
]

MACRO_EVENTS = [
    "fomc", "federal reserve", "fed meeting", "rate decision",
    "cpi", "consumer price index", "inflation data",
    "nfp", "non farm payroll", "jobs report",
    "gdp", "gross domestic product",
    "powell", "yellen", "lagarde",
    "ecb", "boe", "bank of england",
    "may 1", "labor day", "options expiry", "futures expiry"
]


def fetch_rss(feed_name: str, url: str, max_age_hours: int = 6) -> list:
    """Fetch and parse RSS feed, return recent articles."""
    articles = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ClawSentinel/1.0"})
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
            content = resp.read()
        root = ET.fromstring(content)
        channel = root.find("channel"); channel = channel if channel is not None else root
        items = channel.findall("item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")

        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        for item in items[:20]:
            title = (item.findtext("title") or "").strip()
            desc = (item.findtext("description") or item.findtext("summary") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub = item.findtext("pubDate") or item.findtext("{http://www.w3.org/2005/Atom}published") or ""

            # Parse publish time
            pub_time = None
            for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT",
                        "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"]:
                try:
                    pub_time = datetime.strptime(pub.strip(), fmt)
                    if pub_time.tzinfo is None:
                        pub_time = pub_time.replace(tzinfo=timezone.utc)
                    break
                except Exception:
                    continue

            if pub_time and pub_time < cutoff:
                continue

            age_hours = (datetime.now(timezone.utc) - pub_time).total_seconds() / 3600 if pub_time else 3.0

            articles.append({
                "source": feed_name,
                "title": title,
                "desc": re.sub(r"<[^>]+>", "", desc)[:300],
                "link": link,
                "age_hours": age_hours,
                "pub_time": pub_time.isoformat() if pub_time else None
            })

    except Exception as e:
        logger.warning(f"RSS fetch failed [{feed_name}]: {e}")
    return articles


def fetch_fear_greed() -> dict:
    """Fetch Fear & Greed index from alternative.me."""
    try:
        req = urllib.request.Request(
            "https://api.alternative.me/fng/?limit=2",
            headers={"User-Agent": "ClawSentinel/1.0"}
        )
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=8) as resp:
            data = json.loads(resp.read())
        current = data["data"][0]
        previous = data["data"][1] if len(data["data"]) > 1 else current
        current_val = int(current["value"])
        previous_val = int(previous["value"])
        delta = current_val - previous_val
        return {
            "value": current_val,
            "label": current["value_classification"],
            "previous": previous_val,
            "delta": delta,
            "trend": "rising" if delta > 0 else "falling" if delta < 0 else "flat"
        }
    except Exception as e:
        logger.warning(f"Fear/Greed fetch failed: {e}")
        return {"value": 50, "label": "Neutral", "previous": 50, "delta": 0, "trend": "flat"}


def fetch_bybit_funding() -> dict:
    """Fetch funding rates for BTC/ETH/SOL from Bybit."""
    results = {}
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    try:
        for sym in symbols:
            url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={sym}"
            req = urllib.request.Request(url, headers={"User-Agent": "ClawSentinel/1.0"})
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=8) as resp:
                data = json.loads(resp.read())
            tickers = data.get("result", {}).get("list", [])
            if tickers:
                t = tickers[0]
                funding = float(t.get("fundingRate", 0))
                results[sym] = {
                    "funding_rate": funding,
                    "funding_pct": round(funding * 100, 4),
                    "bias": "long_heavy" if funding > 0.0005 else "short_heavy" if funding < -0.0005 else "neutral"
                }
    except Exception as e:
        logger.warning(f"Funding rate fetch failed: {e}")
    return results


def fetch_btc_dominance() -> dict:
    """Fetch BTC dominance from CoinGecko free API."""
    try:
        url = "https://api.coingecko.com/api/v3/global"
        req = urllib.request.Request(url, headers={"User-Agent": "ClawSentinel/1.0"})
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
            data = json.loads(resp.read())
        dom = data.get("data", {}).get("market_cap_percentage", {})
        btc_dom = round(dom.get("btc", 0), 2)
        eth_dom = round(dom.get("eth", 0), 2)
        total_mcap = data.get("data", {}).get("total_market_cap", {}).get("usd", 0)
        mcap_change = data.get("data", {}).get("market_cap_change_percentage_24h_usd", 0)
        return {
            "btc_dominance": btc_dom,
            "eth_dominance": eth_dom,
            "total_mcap_usd": total_mcap,
            "mcap_change_24h": round(mcap_change, 2),
            "altcoin_season": btc_dom < 50
        }
    except Exception as e:
        logger.warning(f"BTC dominance fetch failed: {e}")
        return {"btc_dominance": 55, "eth_dominance": 15, "total_mcap_usd": 0, "mcap_change_24h": 0, "altcoin_season": False}


def fetch_upcoming_macro_events() -> list:
    """
    Hardcoded known high-impact macro events for the next 7 days.
    Falls back to static list since ForexFactory scraping is unreliable.
    In production, replace with Finnhub economic calendar API.
    """
    now = datetime.now(timezone.utc)
    events = []

    # Known events (update weekly or via Finnhub API)
    known_events = [
        {"date": "2026-04-30", "name": "FOMC Rate Decision", "impact": "HIGH", "symbol": "🔴"},
        {"date": "2026-04-30", "name": "BTC Nashville Conference", "impact": "HIGH", "symbol": "🟡"},
        {"date": "2026-05-01", "name": "May Day / NFP", "impact": "HIGH", "symbol": "🔴"},
        {"date": "2026-05-01", "name": "US Labor Data", "impact": "MEDIUM", "symbol": "🟡"},
        {"date": "2026-05-02", "name": "CME Options Expiry", "impact": "MEDIUM", "symbol": "🟡"},
    ]

    for e in known_events:
        try:
            event_date = datetime.strptime(e["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            days_away = (event_date - now).days
            if -1 <= days_away <= 7:
                e["days_away"] = days_away
                e["label"] = "TODAY" if days_away == 0 else f"in {days_away}d" if days_away > 0 else "YESTERDAY"
                events.append(e)
        except Exception:
            pass
    return events


# ══════════════════════════════════════════════════════
# LAYER 1: SIGNAL EXTRACTION
# ══════════════════════════════════════════════════════

def score_article(article: dict) -> dict:
    """Score a single article for bullish/bearish signal strength."""
    text = (article["title"] + " " + article["desc"]).lower()
    age = article.get("age_hours", 3.0)

    # Recency weight
    if age < 1:
        recency = 3.0
    elif age < 3:
        recency = 2.0
    elif age < 6:
        recency = 1.0
    else:
        recency = 0.3

    # Score keywords
    bull_score = 0
    bear_score = 0
    matched_keywords = []
    is_macro = False

    for kw in BULLISH_TIER1:
        if kw in text:
            bull_score += 3 * recency
            matched_keywords.append(f"+{kw}")
    for kw in BULLISH_TIER2:
        if kw in text:
            bull_score += 2 * recency
            matched_keywords.append(f"+{kw}")
    for kw in BULLISH_TIER3:
        if kw in text:
            bull_score += 1 * recency

    for kw in BEARISH_TIER1:
        if kw in text:
            bear_score += 3 * recency
            matched_keywords.append(f"-{kw}")
    for kw in BEARISH_TIER2:
        if kw in text:
            bear_score += 2 * recency
            matched_keywords.append(f"-{kw}")
    for kw in BEARISH_TIER3:
        if kw in text:
            bear_score += 1 * recency

    for kw in MACRO_EVENTS:
        if kw in text:
            is_macro = True
            break

    net_score = bull_score - bear_score
    article["bull_score"] = round(bull_score, 2)
    article["bear_score"] = round(bear_score, 2)
    article["net_score"] = round(net_score, 2)
    article["matched_keywords"] = matched_keywords[:5]
    article["is_macro"] = is_macro
    article["recency"] = recency
    return article


# ══════════════════════════════════════════════════════
# LAYER 2: BAYESIAN EXPECTATION DELTA (BED)
# ══════════════════════════════════════════════════════

def calculate_bed_score(
    news_net: float,
    fear_greed: dict,
    funding: dict,
    dominance: dict,
    macro_events: list
) -> dict:
    """
    BED = Actual Signal Strength - Market Expectation
    
    Market expectation is derived from:
    - Funding rates (what crowd is positioned for)
    - Fear/Greed (market sentiment already priced)
    
    Actual signal from:
    - News scoring
    - Macro event weight
    - Dominance shift
    """

    # Market expectation proxy
    fg_val = fear_greed.get("value", 50)
    fg_normalized = (fg_val - 50) / 50  # -1 to +1

    # Funding rate bias (average across BTC/ETH/SOL)
    funding_scores = []
    for sym, f in funding.items():
        rate = f.get("funding_rate", 0)
        funding_scores.append(rate * 1000)  # scale
    avg_funding = sum(funding_scores) / len(funding_scores) if funding_scores else 0

    market_expectation = (fg_normalized * 3) + (avg_funding * 2)

    # Actual signal strength
    news_signal = news_net * 0.4

    # Macro event multiplier
    macro_weight = 0
    for e in macro_events:
        if e["impact"] == "HIGH":
            macro_weight += 2.0
        elif e["impact"] == "MEDIUM":
            macro_weight += 1.0

    # Dominance signal
    dom_signal = 0
    mcap_change = dominance.get("mcap_change_24h", 0)
    if mcap_change > 3:
        dom_signal = 2
    elif mcap_change > 1:
        dom_signal = 1
    elif mcap_change < -3:
        dom_signal = -2
    elif mcap_change < -1:
        dom_signal = -1

    # Fear/greed momentum
    fg_delta = fear_greed.get("delta", 0)
    fg_momentum = fg_delta * 0.1

    actual_signal = news_signal + macro_weight + dom_signal + fg_momentum

    # BED calculation
    bed = actual_signal - market_expectation

    # Normalize to -10 to +10
    bed_normalized = max(-10, min(10, bed))

    return {
        "bed_score": round(bed_normalized, 2),
        "actual_signal": round(actual_signal, 2),
        "market_expectation": round(market_expectation, 2),
        "components": {
            "news_signal": round(news_signal, 2),
            "macro_weight": round(macro_weight, 2),
            "dom_signal": round(dom_signal, 2),
            "fg_momentum": round(fg_momentum, 2),
        },
        "interpretation": (
            "Market UNDERPRICING bullish move — FRONT-RUN LONG" if bed_normalized > 3 else
            "Mild bullish edge — lean LONG" if bed_normalized > 1 else
            "Market OVERPRICING bearish risk — FADE BEARS" if bed_normalized < -3 else
            "Mild bearish pressure — reduce size" if bed_normalized < -1 else
            "Fairly priced — neutral bias"
        )
    }


# ══════════════════════════════════════════════════════
# LAYER 3: SENTINEL SCORE (0-100)
# ══════════════════════════════════════════════════════

def calculate_sentinel_score(
    bed: dict,
    fear_greed: dict,
    funding: dict,
    dominance: dict,
    macro_events: list
) -> dict:
    """Combine all signals into a single 0-100 Sentinel Score."""

    # Base from BED (-10 to +10 → 0 to 100)
    bed_component = (bed["bed_score"] + 10) * 5  # 0-100

    # Fear/Greed component (direct)
    fg_component = fear_greed.get("value", 50)

    # Funding component
    funding_values = [f.get("funding_rate", 0) for f in funding.values()]
    avg_funding = sum(funding_values) / len(funding_values) if funding_values else 0
    funding_component = 50 + (avg_funding * 10000)  # scale to 0-100 range
    funding_component = max(0, min(100, funding_component))

    # Macro event boost
    macro_boost = sum(3 if e["impact"] == "HIGH" else 1 for e in macro_events if e.get("days_away", 99) <= 1)
    macro_boost = min(macro_boost, 10)

    # Market cap momentum
    mcap_change = dominance.get("mcap_change_24h", 0)
    mcap_component = 50 + (mcap_change * 3)
    mcap_component = max(0, min(100, mcap_component))

    # Weighted average
    sentinel = (
        bed_component * 0.35 +
        fg_component * 0.25 +
        funding_component * 0.15 +
        mcap_component * 0.15 +
        (50 + macro_boost * 5) * 0.10
    )
    sentinel = round(max(0, min(100, sentinel)), 1)

    # Label
    if sentinel >= 80:
        label = "💚 STRONG BULL"
        bias = "LONG"
        sizing = "1.5x — Aggressive"
        risk = "MEDIUM-HIGH"
    elif sentinel >= 60:
        label = "🟢 WEAK BULL"
        bias = "LONG"
        sizing = "1.0x — Standard"
        risk = "MEDIUM"
    elif sentinel >= 40:
        label = "🟡 NEUTRAL"
        bias = "NEUTRAL"
        sizing = "0.5x — Reduced"
        risk = "LOW"
    elif sentinel >= 20:
        label = "🟠 WEAK BEAR"
        bias = "SHORT or WAIT"
        sizing = "0.5x — Defensive"
        risk = "MEDIUM"
    else:
        label = "🔴 STRONG BEAR"
        bias = "AVOID or SHORT"
        sizing = "0x — Stay out"
        risk = "HIGH"

    return {
        "score": sentinel,
        "label": label,
        "bias": bias,
        "sizing": sizing,
        "risk": risk,
        "components": {
            "bed": round(bed_component, 1),
            "fear_greed": round(fg_component, 1),
            "funding": round(funding_component, 1),
            "mcap": round(mcap_component, 1),
        }
    }


# ══════════════════════════════════════════════════════
# LAYER 4: GROQ AI SYNTHESIS
# ══════════════════════════════════════════════════════

def synthesize_with_ai(sentinel: dict, bed: dict, fear_greed: dict,
                        top_headlines: list, macro_events: list) -> str:
    """Send compressed macro context to Groq for final synthesis."""
    try:
        import urllib.request, json

        headlines_str = "\n".join([f"- {h['title']} [{h['source']}]" for h in top_headlines[:5]])
        events_str = "\n".join([f"- {e['name']} ({e['label']}, {e['impact']} impact)" for e in macro_events[:3]])

        prompt = f"""You are CLAWTCHER SENTINEL, an elite macro intelligence agent for crypto trading.

CURRENT MACRO CONTEXT:
Sentinel Score: {sentinel['score']}/100 ({sentinel['label']})
Bayesian Edge (BED): {bed['bed_score']}/10 — {bed['interpretation']}
Fear & Greed: {fear_greed['value']}/100 ({fear_greed['label']}) trending {fear_greed['trend']}
Session Bias: {sentinel['bias']}
Position Sizing: {sentinel['sizing']}

TOP HEADLINES (last 6hrs):
{headlines_str}

UPCOMING MACRO EVENTS:
{events_str}

In 3-4 sentences, give a sharp trading intelligence briefing:
1. What is the macro regime right now?
2. What is the highest probability move in next 24-48hrs?
3. Which pairs to focus on and why?
4. Any risks to watch?

Be direct, quantitative, actionable. No fluff."""

        payload = json.dumps({
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 400
        }).encode()

        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=20) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        logger.warning(f"AI synthesis failed: {e}")
        return f"Sentinel Score {sentinel['score']}/100 — {sentinel['label']}. Bias: {sentinel['bias']}."


# ══════════════════════════════════════════════════════
# MAIN: GET SENTINEL REPORT
# ══════════════════════════════════════════════════════

def get_sentinel_report() -> dict:
    """Run full Sentinel analysis. Returns structured report."""
    logger.info("CLAWTCHER SENTINEL: Starting analysis...")
    start = time.time()

    # Parallel data fetch
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {
            ex.submit(fetch_fear_greed): "fear_greed",
            ex.submit(fetch_bybit_funding): "funding",
            ex.submit(fetch_btc_dominance): "dominance",
            ex.submit(fetch_upcoming_macro_events): "macro_events",
        }
        for feed_name, url in RSS_FEEDS:
            futures[ex.submit(fetch_rss, feed_name, url)] = f"rss_{feed_name}"

        results = {}
        rss_articles = []
        for future in as_completed(futures):
            key = futures[future]
            try:
                val = future.result()
                if key.startswith("rss_"):
                    rss_articles.extend(val)
                else:
                    results[key] = val
            except Exception as e:
                logger.warning(f"Future failed [{key}]: {e}")

    fear_greed = results.get("fear_greed", {"value": 50, "label": "Neutral", "delta": 0, "trend": "flat"})
    funding = results.get("funding", {})
    dominance = results.get("dominance", {})
    macro_events = results.get("macro_events", [])

    # Score all articles
    scored = [score_article(a) for a in rss_articles]
    scored.sort(key=lambda x: abs(x["net_score"]), reverse=True)

    # Top headlines (highest absolute signal)
    top_headlines = scored[:8]
    macro_headlines = [a for a in scored if a["is_macro"]][:3]

    # Total news signal
    total_bull = sum(a["bull_score"] for a in scored)
    total_bear = sum(a["bear_score"] for a in scored)
    news_net = total_bull - total_bear

    # BED calculation
    bed = calculate_bed_score(news_net, fear_greed, funding, dominance, macro_events)

    # Sentinel score
    sentinel = calculate_sentinel_score(bed, fear_greed, funding, dominance, macro_events)

    # AI synthesis
    ai_brief = synthesize_with_ai(sentinel, bed, fear_greed, top_headlines, macro_events)

    elapsed = round(time.time() - start, 1)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "elapsed_sec": elapsed,
        "sentinel": sentinel,
        "bed": bed,
        "fear_greed": fear_greed,
        "funding": funding,
        "dominance": dominance,
        "macro_events": macro_events,
        "news_stats": {
            "total_articles": len(scored),
            "total_bull": round(total_bull, 1),
            "total_bear": round(total_bear, 1),
            "net": round(news_net, 1)
        },
        "top_headlines": top_headlines[:5],
        "macro_headlines": macro_headlines,
        "ai_brief": ai_brief
    }

    logger.info(f"SENTINEL complete in {elapsed}s — Score: {sentinel['score']}/100 ({sentinel['label']})")
    return report


def format_sentinel_telegram(report: dict) -> str:
    """Format Sentinel report for Telegram."""
    s = report["sentinel"]
    b = report["bed"]
    fg = report["fear_greed"]
    d = report["dominance"]
    events = report["macro_events"]
    funding = report["funding"]
    stats = report["news_stats"]

    # Funding summary
    funding_lines = []
    for sym, f in funding.items():
        bias_icon = "🟢" if f["bias"] == "neutral" else "🔴" if f["bias"] == "long_heavy" else "🔵"
        funding_lines.append(f"  {bias_icon} {sym}: {f['funding_pct']:+.4f}%")

    # Events
    event_lines = []
    for e in events[:4]:
        impact_icon = "🔴" if e["impact"] == "HIGH" else "🟡"
        event_lines.append(f"  {impact_icon} {e['name']} ({e['label']})")

    # Top headlines
    headline_lines = []
    for h in report["top_headlines"][:4]:
        icon = "📈" if h["net_score"] > 0 else "📉"
        headline_lines.append(f"  {icon} {h['title'][:60]}...")

    text = (
        f"🧠 *CLAWTCHER SENTINEL*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"*SENTINEL SCORE: {s['score']}/100*\n"
        f"{s['label']}\n\n"
        f"*Bayesian Edge (BED):* `{b['bed_score']:+.1f}/10`\n"
        f"_{b['interpretation']}_\n\n"
        f"*Session Bias:* `{s['bias']}`\n"
        f"*Sizing:* `{s['sizing']}`\n"
        f"*Risk:* `{s['risk']}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*MARKET SIGNALS*\n"
        f"  Fear/Greed: `{fg['value']}/100` ({fg['label']}) {fg['trend']}\n"
        f"  BTC Dominance: `{d.get('btc_dominance', 0)}%`\n"
        f"  Market Cap 24h: `{d.get('mcap_change_24h', 0):+.1f}%`\n"
        f"  News: `{stats['total_articles']} articles` | Bull: `{stats['total_bull']:.0f}` Bear: `{stats['total_bear']:.0f}`\n\n"
        f"*FUNDING RATES*\n"
        + "\n".join(funding_lines) + "\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*MACRO CALENDAR*\n"
        + ("\n".join(event_lines) if event_lines else "  No high-impact events found") + "\n\n"
        f"*TOP SIGNALS*\n"
        + "\n".join(headline_lines) + "\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*AI BRIEF*\n"
        f"_{report['ai_brief']}_\n\n"
        f"⚙️ _Clawtcher Sentinel | {report['elapsed_sec']}s | Admin Only_"
    )
    return text


def send_sentinel_telegram(report: dict):
    """Send Sentinel report to admin via Telegram."""
    text = format_sentinel_telegram(report)
    try:
        payload = json.dumps({
            "chat_id": ADMIN_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as resp:
            result = json.loads(resp.read())
        if result.get("ok"):
            logger.info("Sentinel report sent to Telegram")
        else:
            logger.error(f"Telegram send failed: {result}")
    except Exception as e:
        logger.error(f"Telegram send error: {e}")


def get_sentinel_context_for_scan() -> str:
    """
    Lightweight version for injecting into AI scan prompt.
    Runs faster, returns compressed context string.
    """
    try:
        fg = fetch_fear_greed()
        funding = fetch_bybit_funding()
        events = fetch_upcoming_macro_events()

        # Quick RSS scan (2 sources only for speed)
        articles = []
        for name, url in RSS_FEEDS[:2]:
            articles.extend(fetch_rss(name, url, max_age_hours=3))
        scored = sorted([score_article(a) for a in articles],
                       key=lambda x: abs(x["net_score"]), reverse=True)

        news_net = sum(a["net_score"] for a in scored)
        bias = "BULLISH" if news_net > 2 else "BEARISH" if news_net < -2 else "NEUTRAL"

        event_str = ", ".join([e["name"] for e in events[:2]]) if events else "None"
        top_headline = scored[0]["title"] if scored else "No recent headlines"

        btc_funding = funding.get("BTCUSDT", {}).get("funding_pct", 0)

        context = (
            f"MACRO CONTEXT: {bias} bias | "
            f"Fear/Greed: {fg['value']}/100 ({fg['label']}) | "
            f"BTC Funding: {btc_funding:+.4f}% | "
            f"Key Events: {event_str} | "
            f"Top Signal: {top_headline[:80]}"
        )
        return context
    except Exception as e:
        logger.warning(f"Sentinel context failed: {e}")
        return "MACRO CONTEXT: Unavailable"


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"

    if mode == "report":
        print("Running full Sentinel analysis...")
        report = get_sentinel_report()
        print(json.dumps(report, indent=2, default=str))
        send_sentinel_telegram(report)

    elif mode == "context":
        ctx = get_sentinel_context_for_scan()
        print(ctx)

    elif mode == "test":
        print("Testing individual components...")
        print("Fear/Greed:", fetch_fear_greed())
        print("Funding:", fetch_bybit_funding())
        print("Dominance:", fetch_btc_dominance())
        print("Events:", fetch_upcoming_macro_events())
        articles = fetch_rss("CoinTelegraph", "https://cointelegraph.com/rss")
        print(f"RSS articles: {len(articles)}")
