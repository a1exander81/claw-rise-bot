# 📦 Claw_Rise_bot — Deliverables & File Map

All modules are implemented and ready for integration.

---

## 🗂️ Project Tree (relevant files)

```
claw-rise-bot/
├── config/
│   └── config.yaml                # Central configuration (risk, AI, sessions)
├── src/
│   ├── ai/
│   │   ├── indicators.py          # pandas-ta indicators (RSI, MACD, EMA, volume)
│   │   └── signal_engine.py       # StepFun TA + filters → BUY/SELL/NEUTRAL
│   ├── exchange/
│   │   └── bingx.py               # BingX REST adapter (isolated perpetuals)
│   ├── risk/
│   │   └── position_manager.py    # sizing, SL/TP, trailing, mock mode
│   ├── bot/
│   │   ├── executor.py            # main loop, scheduler, manual, auto-close
│   │   └── telegram_bot.py        # 0-Type inline UI, menus, live PnL
│   ├── ui/
│   │   └── pnl_card.py            # meme image generator (hype/sad)
│   ├── social/
│   │   └── x_broadcast.py         # auto-post wins + random hype drops
│   ├── data/
│   │   └── pipeline.py            # 5m OHLCV Parquet cache + backfill
│   ├── backtest/
│   │   ├── engine.py              # walk-forward simulation
│   │   ├── hyperopt.py            # param sweep (Bayesian/random)
│   │   └── metrics.py             # Sharpe, drawdown, win rate, R:R
│   └── health/
│       └── monitor.py             # /health endpoint, supervisor, log rotation
├── web/
│   ├── Dockerfile
│   ├── server.py                  # FastAPI dashboard server
│   └── static/                    # HTML/CSS/JS (Freqtrade‑style dark theme)
├── scripts/
│   ├── test_bingx.py              # CLI test for exchange adapter (dry-run)
│   ├── download_historical.py     # backfill 5m candles
│   ├── run_bot.py                 # manual bot runner (non‑supervisor)
│   └── run_supervisor.sh          # starts monitor + bot
├── data/                          # SQLite DB + Parquet candles (mounted)
├── logs/                          # rotated logs (mounted)
├── generated-cards/               # PnL meme images (mounted)
├── templates/                     # image assets for PnL cards
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── requirements.txt
├── requirements-web.txt
├── LAUNCH_CHECKLIST.md
├── INTEGRATION_SUMMARY.md
└── README.md
```

---

## ✅ Module Status (12/12)

| # | Module | Key Files | Status |
|---|--------|-----------|--------|
| 1 | Core Scaffold | `config/`, `src/`, `data/`, `logs/`, `scripts/`, `Dockerfile`, `docker-compose.yml`, `README.md` | ✅ |
| 2 | BingX Adapter | `src/exchange/bingx.py`, `scripts/test_bingx.py` | ✅ |
| 3 | AI Signal Engine | `src/ai/signal_engine.py`, `src/ai/indicators.py` | ✅ |
| 4 | Risk Manager | `src/risk/position_manager.py` | ✅ |
| 5 | Telegram UI | `src/bot/telegram_bot.py`, `ui/layouts.py` | ✅ |
| 6 | PnL Card Generator | `src/ui/pnl_card.py`, `templates/` | ✅ |
| 7 | Health Monitor | `src/health/monitor.py`, `scripts/run_supervisor.sh` | ✅ |
| 8 | X Broadcast | `src/social/x_broadcast.py` | ✅ |
| 9 | Data Pipeline | `src/data/pipeline.py`, `scripts/download_historical.py` | ✅ |
|10 | Backtesting & Hyperopt | `src/backtest/engine.py`, `src/backtest/hyperopt.py`, `src/backtest/metrics.py` | ✅ |
|11 | WebUI Dashboard | `web/server.py`, `web/static/` | ✅ |
|12 | Core Executor | `src/bot/executor.py`, `scripts/run_bot.py` | ✅ |

---

## 📄 Final Integration Artifacts (just created)

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Orchestrates bot + webui + redis services |
| `.env.example` | All required environment variables (fill & rename to `.env`) |
| `LAUNCH_CHECKLIST.md` | Step‑by‑step setup, verification, first trade |
| `INTEGRATION_SUMMARY.md` | Architecture diagram, API reference, data flow |
| `README.md` | Project overview, quick start, troubleshooting |
| `Dockerfile` | Multi‑stage build for bot container |
| `web/Dockerfile` | Build for WebUI service |
| `requirements.txt` | Python dependencies (bot) |
| `requirements-web.txt` | Python dependencies (WebUI) |
| `scripts/run_supervisor.sh` | Supervisor launcher (health + bot) |

---

## 🔧 What’s Left Before First Run?

1. **Fill `.env`** with real keys (BingX, StepFun, Telegram, optional Twitter)
2. **Build images** (`docker-compose build`)
3. **Backfill candles** (`docker-compose exec bot python -m src.data.pipeline --backfill --days 30`)
4. **Dry‑run test** (`BINGX_TEST_MODE=true`) → manual trade via Telegram
5. **Go live** (`BINGX_TEST_MODE=false`) → wait for next session open

Everything else is wired and ready. All modules respect your constraints:
- Isolated margin, 1–2% risk, 50X default (max 100X)
- 3 auto trades/day, unlimited manual
- 0‑Type Telegram UI
- Hype/sad PnL cards + X broadcast

**Confirm the two parameters** (leverage cap 100X, session times as listed) and I’ll finalize the handoff with a concise “ready to launch” summary plus next steps.
