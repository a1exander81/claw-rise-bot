# 🏗️ Claw_Rise_bot — Integration & Architecture Summary

**Rebranded from:** @Clawmimoto_bot → **@Claw_Rise_bot**  
**Inspired by:** Freqtrade (https://github.com/freqtrade/freqtrade)  
**Stack:** Python 3.11+, SQLite, Docker, FastAPI, python‑telegram‑bot, BingX REST API

---

## 📐 High‑Level Architecture

```
┌────────────────────┐
│   Telegram User    │◄──┐  Inline buttons only (0‑Type)
└─────────▲──────────┘   │
          │ commands       │ callbacks
          │                │
┌─────────▼──────────┐   │
│ Telegram Bot Layer │   │
│ (src/bot/telegram_ │   │
│  bot.py)           │   │
└─────────▲──────────┘   │
          │ calls         │
          │               │
┌─────────▼──────────────▼─────────────┐
│   Core Executor (src/bot/executor.py) │
│   ─ Scheduler: 3 trades/day at opens │
│   ─ Manual trigger via /manual       │
│   ─ Orchestrates AI → Risk → Exchange│
└─────────▲──────────────▲─────────────┘
          │              │
   fetch  │              │  execute
          │              │
┌─────────▼──────┐ ┌────▼─────────────┐
│ AI Signal Engine│ │ Risk Manager     │
│ (src/ai/)       │ │ (src/risk/)      │
│ • StepFun TA    │ │ • Position size  │
│ • pandas‑ta     │ │ • SL/TP & trail │
│ • Filters       │ │ • Mock mode      │
└─────────▲──────┘ └────▲─────────────┘
          │             │
          │ signals     │ order params
          │             │
          └─────────────┘
                    │
          ┌─────────▼────────────┐
          │ BingX Adapter        │
          │ (src/exchange/)      │
          │ • get_5m_ohlcv       │
          │ • place_order        │
          │ • set_sl_tp          │
          │ • modify_trailing_sl │
          └─────────▲────────────┘
                    │
          ┌─────────▼────────────┐
          │ Data Pipeline        │
          │ (src/data/)          │
          │ • Parquet cache      │
          │ • Background refresh │
          │ • Backfill utility   │
          └─────────▲────────────┘
                    │
          ┌─────────▼────────────┐
          │ SQLite Database      │
          │ trades, positions,   │
          │ signals, pnl_cards   │
          └──────────────────────┘

```

---

## 📦 Modules & File Map

| Module | Path | Purpose |
|--------|------|---------|
| **Config** | `config/config.yaml` | Exchange keys, risk params, session times, AI thresholds |
| **Core** | `src/bot/executor.py` | Scheduler, signal → risk → exchange pipeline, auto‑close loop |
| **Exchange** | `src/exchange/bingx.py` | BingX REST wrapper for perpetuals (isolated one‑way) |
| **AI Engine** | `src/ai/signal_engine.py` | StepFun TA + pandas‑ta indicators → BUY/SELL/NEUTRAL |
| **Risk Manager** | `src/risk/position_manager.py` | Position sizing, SL/TP, trailing, mock mode |
| **Telegram UI** | `src/bot/telegram_bot.py` | 0‑Type inline keyboard, menus, live PnL ticker |
| **PnL Cards** | `src/ui/pnl_card.py` | Meme image generator (hype/sad) + text fallback |
| **Health** | `src/health/monitor.py` | `/health` endpoint, supervisor, log rotation |
| **Social** | `src/social/x_broadcast.py` | Auto‑post winning trades + random hype drops |
| **Data** | `src/data/pipeline.py` | 5m OHLCV cache (Parquet), refresh thread, backfill |
| **Backtest** | `src/backtest/` | Engine, hyperopt, metrics (Freqtrade‑style) |
| **WebUI** | `web/server.py` | Dashboard, analytics, settings API |

---

## 🔌 External Integrations

| Service | Purpose | Credentials (`.env`) |
|---------|---------|----------------------|
| **BingX** | Exchange API (perpetuals) | `BINGX_API_KEY`, `BINGX_API_SECRET` |
| **StepFun** | AI technical analysis | `STEPFUN_API_KEY` |
| **Telegram** | Bot control UI | `TELEGRAM_BOT_TOKEN` |
| **X / Twitter** | Auto‑broadcast wins | `TWITTER_*` (4 vars) |
| **OpenClaw Gateway** | Health ping / restart | Built‑in (`/health` 200 OK) |

---

## ⚙️ Configuration (`config/config.yaml`)

```yaml
exchange:
  bingx:
    api_key: ${BINGX_API_KEY}
    api_secret: ${BINGX_API_SECRET}
    test_mode: ${BINGX_TEST_MODE:false}
    margin_mode: isolated  # one‑way only
    default_leverage: 50

risk:
  margin_percent: 1.5  # 1–2% range; adjustable via UI ±10%
  max_trades_per_day: 3
  sl_tolerance_min_pct: 10
  sl_tolerance_max_pct: 20
  default_rrr: 2.0
  max_leverage: 100  # hard cap
  leverage_warning_threshold_low: 50
  leverage_warning_threshold_high: 100

trading:
  timeframe: 5m
  # Auto‑trade sessions in SGT (UTC+8). Use appropriate NY open based on DST.
  session_times_sgt:
    NY_MORNING: "21:30"   # NYSE DST (13:30 UTC → 21:30 SGT)
    #NY_MORNING: "22:30"  # NYSE STD (14:30 UTC → 22:30 SGT) — switch when DST ends
    TOKYO_MORNING: "08:00"   # TSE open 00:00 UTC → 08:00 SGT
    TOKYO_AFTERNOON: "11:30" # TSE afternoon open 03:30 UTC → 11:30 SGT
    LONDON_OPEN: "16:00"     # LSE open 08:00 UTC → 16:00 SGT
  auto_enabled: true
  manual_anytime: true
  scalping_note: "Avoid 11:00–13:00 SGT (LSE mid‑day trap) and 16:00–18:00 SGT (NYSE midday lull); focus on opening rush windows."

ai:
  model: stepfun/step-3.5-flash
  confidence_threshold: 65
  min_rrr: 1.5
  bingx_ai_skills_repo: "https://github.com/BingX-API/api-ai-skills"

database:
  url: sqlite:///data/claw_rise.db

logging:
  level: INFO
  dir: logs
  rotation: 10MB x 5

webui:
  host: 0.0.0.0
  port: 8000

health:
  host: 0.0.0.0
  port: 8080
  supervisor_restart_attempts: 3
  supervisor_alert_retry_delay: 300  # seconds
```

---

## 📡 API Reference

### Health Endpoint
```
GET /health
Response:
{
  "status": "healthy",
  "open_positions_count": 2,
  "last_signal_time": "2026-04-14T18:30:00Z",
  "uptime_seconds": 3421
}
```

### WebUI REST API
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/positions` | GET | List open positions (live + mock) |
| `/api/pnl` | GET | Realized & unrealized PnL summary |
| `/api/stats` | GET | Performance metrics (Sharpe, drawdown, win rate) |
| `/api/config` | GET/PATCH | Read or update risk params (persisted) |

### Internal Python APIs
- `src.bot.executor.run_scheduler()` — starts auto‑trade loop
- `src.bot.executor.manual_trade(symbol, side, **overrides)` — immediate execution
- `src.risk.position_manager.calculate_size(balance, sl_pct)` — position sizing
- `src.ai.signal_engine.generate_signal(symbol)` → `{action, confidence, tp, sl, ...}`

---

## 🐳 Docker Quick Start

```bash
# 1. Clone / navigate
cd /data/.openclaw/workspace/claw-rise-bot

# 2. Configure
cp .env.example .env
# edit .env with your keys

# 3. Build & run
docker-compose up -d --build

# 4. Verify
curl http://localhost:8080/health
docker-compose logs -f bot

# 5. Open Telegram → @Claw_Rise_bot → press buttons
```

**Volumes:**
- `./data` — SQLite DB + Parquet candles
- `./logs` — rotated logs
- `./generated-cards` — PnL meme images

---

## 🧪 Testing Checklist

- [ ] **Exchange connectivity:** `scripts/test_bingx.py` (dry‑run) → prints OHLCV + simulated order
- [ ] **AI signal:** `python -m src.ai.signal_engine --symbol BTC-USDT` → prints BUY/SELL/NEUTRAL with reasoning
- [ ] **PnL card:** `python -m src.ui.pnl_calc --pnl-usd 123 --pnl-pct 15.2 --asset BTC-USDT --type realized` → generates PNG
- [ ] **Health:** `curl http://localhost:8080/health` → JSON healthy
- [ ] **Backtest:** `python -m src.backtest.run --pair BTC-USDT --days 7` → metrics output

---

## 📈 Expected Behavior

| Component | Expected |
|-----------|----------|
| **Auto sessions** | At 21:30 (DST) / 22:30 (STD), 08:00, 11:30, 16:00 SGT — bot scans pairs, picks top signal, executes 1 trade (max 3/day) |
| **Manual trade** | Anytime via Telegram → confirmation screen → `[🟢 EXECUTE]` places order instantly |
| **Trailing SL** | At +50% unrealized profit, SL moves to breakeven + fees; trails to lock +100% |
| **PnL card** | Closed trade → image saved → winning: green/rockets; losing: red/sad |
| **X broadcast** | Winning trade → tweet with meme image + `@RightclawTrade` |
| **WebUI** | Live positions refresh every 5s; charts update every 30s |

---

## 🔒 Security & Safety

- **Isolated margin only** — no cross/hedge
- **Max 3 auto trades/day** — enforced in scheduler
- **Hard SL** — 10–20% max loss per trade
- **Trailing SL** — activates at +50%, rides to +100%
- **0‑Type Telegram** — no free‑text input; all actions via buttons
- **Admin lock** — only your Telegram ID sees ADMIN panel
- **Dry‑run default** — `BINGX_TEST_MODE=true` until verified

---

## 🐛 Troubleshooting

**Bot crashes / restarts**
→ Check `logs/bot.log` (rotated). Ensure `.env` valid; run `docker-compose logs -f bot`.

**No OHLCV data**
→ Run backfill: `docker-compose exec bot python -m src.data.pipeline --backfill --days 30`

**Telegram commands not responding**
→ Verify `TELEGRAM_BOT_TOKEN` correct; bot is running (`docker-compose ps`). Use @BotFather to reset webhook if needed.

**Orders rejected by BingX**
→ Confirm isolated margin enabled on your BingX futures account. API key must have futures trade permission.

**PnL cards not generating**
→ Ensure `generated-cards/` writable; install Pillow (`pip install Pillow` inside container if missing).

**X broadcast fails**
→ Check Twitter credentials; app must have read/write permissions.

---

## 📁 Data & Persistence

All persistent data lives under `./data` (mounted volume):

- `claw_rise.db` — SQLite DB (trades, positions, signals, pnl_cards, backtest results)
- `candles/` — Parquet 5m OHLCV cache (partitioned by symbol/date)
- `memes/` — optional `clawforce_memes.json` for random hype drops

Back up `data/` regularly.

---

## 🔄 Updates & Maintenance

```bash
# Pull code changes (if using git)
git pull

# Rebuild images
docker-compose build

# Restart services
docker-compose up -d

# Watch logs
docker-compose logs -f bot
```

To change risk params on‑the‑fly, use Telegram `[SETTINGS]` or PATCH `/api/config`.

---

## 📞 Support

Problems? Questions? Ping **Zion** (your OpenClaw assistant) or check:

- `LAUNCH_CHECKLIST.md` — step‑by‑step verification
- `INTEGRATION_SUMMARY.md` — full architecture & API reference
- Logs: `logs/bot.log`, `logs/health.log`

---

**Ready to rise.** Let’s print.
