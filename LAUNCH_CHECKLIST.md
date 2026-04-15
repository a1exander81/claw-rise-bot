# 🚀 Claw_Rise_bot — Launch Checklist

**Rebrand:** @Claw_Rise_bot | **AI:** StepFun 3.5‑Flash | **Exchange:** BingX perpetuals (isolated)

---

## Phase 1 — Prerequisites & Secrets

- [ ] **Get Telegram Bot Token**
  - Talk to @BotFather → `/newbot` → name: `Claw Rise Trading Bot`, username: `Claw_Rise_bot`
  - Save token to `TELEGRAM_BOT_TOKEN` in `.env`

- [ ] **Get BingX API Keys**
  - Log into BingX → API Management → Create API key with permissions: Spot read/write, Futures read/write, Margin isolated
  - Save `BINGX_API_KEY` and `BINGX_API_SECRET` to `.env`
  - **⚠️ Start in TEST mode:** set `BINGX_TEST_MODE=true` until you verify dry‑run trades

- [ ] **StepFun API Key**
  - Obtain from StepFun console → save to `STEPFUN_API_KEY` in `.env`

- [ ] **X / Twitter (optional)**
  - Create Twitter app → get API key/secret + access token/secret
  - Save to `.env` to enable auto‑broadcast

- [ ] **Set Admin Telegram ID**
  - Your ID is `7093901111` (Rentardio) — already in config as `TELEGRAM_ADMIN_ID`
  - If different, update `.env`

- [ ] **Configure session times for DST**
  - Current period (Apr 2026): **DST active** (US DST started Mar 8, 2026; ends Nov 1, 2026)
  - Ensure `.env` has `SESSION_NY_OPEN=21:30` (DST). During STD (Nov–Mar) switch to `22:30`.
  - Alternatively, adjust in `config/config.yaml` under `trading.session_times_sgt.NY_MORNING`.

---

## Phase 2 — Local Build & Docker

```bash
cd /data/.openclaw/workspace/claw-rise-bot

# 1. Copy environment template
cp .env.example .env
# Edit .env with your secrets (use nano/vim or any editor)

# 2. Pull images & build containers
docker-compose pull
docker-compose build --no-cache

# 3. Verify health endpoint
docker-compose up -d
sleep 5
curl http://localhost:8080/health  # should return {"status":"healthy",...}
```

- [ ] **Health check passes** — `status: healthy`, uptime increasing

---

## Phase 3 — Historical Data Backfill

```bash
# Fetch 30 days of 5m candles for default pairs (BTC, ETH, SOL, BNB)
docker-compose exec bot python -m src.data.pipeline --backfill --days 30
```

- [ ] **Backfill completes** without errors; check `data/candles/` for Parquet files

---

## Phase 4 — Dry‑Run Validation

```bash
# 1. Ensure BingX test mode is ON in .env
export BINGX_TEST_MODE=true

# 2. Restart bot
docker-compose restart bot

# 3. Watch logs for startup
docker-compose logs -f bot

# 4. Trigger manual test trade via Telegram:
#    Open chat with @Claw_Rise_bot → press [SCAN] → pick BTC-USDT → confirm trade
#    Expected: Order simulation, no real funds moved
```

- [ ] **Dry‑run trade appears** in logs with “SIMULATED” flag
- [ ] **PnL card generated** in `generated-cards/` (check PNG + text fallback)

---

## Phase 5 — Enable Live Trading

```bash
# 1. Switch BingX to live
sed -i 's/BINGX_TEST_MODE=true/BINGX_TEST_MODE=false/' .env

# 2. Adjust risk params (optional)
#    DEFAULT_MARGIN_PERCENT=1.5  (1–2% range)
#    DEFAULT_LEVERAGE=50

# 3. Restart
docker-compose restart bot
```

- [ ] **Bot connects to BingX** (check logs: “Exchange authenticated”)
- [ ] **Health endpoint still healthy**
- [ ] **Auto‑session trigger:** Wait for next market open (NY 21:30 SGT during DST, 22:30 during STD; Tokyo 08:00/11:30; London 16:00). Bot should scan and place up to 3 trades automatically.

---

## Phase 6 — Telegram UI Verification

- [ ] **Main menu** shows: `[STATUS] [SCAN] [AI SIGNALS] [POSITIONS] [SETTINGS] [ADMIN]`
- [ ] **Asset grid** lists tradable pairs (BTC-USDT, ETH-USDT, SOL-USDT, BNB-USDT by default)
- [ ] **Hot Pairs row** displays top 4 AI movers with 🟢🦞 visuals
- [ ] **Trade confirmation** shows Entry, SL, TP, Leverage, Margin % with +‑10% buttons
- [ ] **Position detail** updates in‑place every 3s with live PnL
- [ ] **Admin panel** (your ID only) shows: Forward Signal, Post to X, Review Learnings

---

## Phase 7 — X Broadcast (Optional)

- [ ] **Winning trade card** auto‑posts to @RightclawTrade with meme image
- [ ] **Random hype drops** appear 1–2 times/day (ensure `data/memes/clawforce_memes.json` exists; create if missing)

---

## Phase 8 — WebUI & Analytics

```bash
# Access at http://<your-vps-ip>:8000
# - Dashboard: open positions, PnL summary
# - Analytics: Sharpe, drawdown, win rate
# - Settings: tweak risk params via API (also syncs to bot)
```

- [ ] **WebUI loads**, shows live data from bot
- [ ] **Charts render**, stats update every 30s

---

## Phase 9 — Backtesting & Hyperopt (Optional)

```bash
# Backtest a pair over last 30 days
docker-compose exec bot python -m src.backtest.run --pair BTC-USDT --days 30

# Run hyperopt to optimize params
docker-compose exec bot python -m src.backtest.hyperopt --pair BTC-USDT --trials 100
```

- [ ] **Backtest results** saved; best params appear in `src/backtest/best_params.json`

---

## Phase 10 — Ongoing Ops

- **Logs:** `docker-compose logs -f bot`
- **Health:** `curl http://localhost:8080/health`
- **Restart bot:** `docker-compose restart bot`
- **Update code:** pull changes → `docker-compose build` → `docker-compose up -d`

---

## 🆘 Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Bot dies after 14s | Supervisor not running | `docker-compose ps` → ensure `bot` is up; check `logs/` |
| No OHLCV data | Backfill not run | Run backfill (Phase 3) |
| No Telegram commands | Wrong bot token | Verify `TELEGRAM_BOT_TOKEN` in `.env`; restart |
| Orders rejected by BingX | Isolated margin not enabled on account | Enable isolated margin for futures in BingX UI |
| PnL cards not generating | Pillow missing or permissions | `pip install Pillow` in Dockerfile; ensure `generated-cards/` is writable |
| X posts fail | Missing Twitter credentials | Check `.env` keys; verify app permissions (read/write) |

---

**All set.** Once every box is checked, your AI‑powered 5m sniper bot is live.

Need help? Ping me (Zion) anytime.
