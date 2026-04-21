# Docker Deployment — ClawForge MTF Bot

## Overview

This stack runs the ClawForge trading bot in two isolated containers:
- `freqtrade` — Trading engine + REST API (port 8080)
- `telegram-ui` — Telegram bot interface (no external ports)

Both share:
- `user_data/` volume (dry-run DB, logs, hyperopt results)
- `configs/`, `strategies/`, `clawforge/` (read-only code mounts)
- Docker network `claw-isolation`

---

## Prerequisites

- Docker Engine ≥ 20.10
- Docker Compose plugin (`docker compose`) or standalone `docker-compose`
- Your VPS has port 8080 free (or change mapping in `docker-compose.yml`)

---

## Quick Start

```bash
cd /data/.openclaw/workspace/clawmimoto-bot

# 1. Build images (first time only — takes ~5–10 min)
docker compose build

# 2. Stop any old non-Docker processes (if still running)
# (skip if you're fresh)
pkill -f "freqtrade"
pkill -f "clawforge.telegram_ui"

# 3. Start stack
docker compose up -d

# 4. Check status
docker compose ps
docker compose logs -f freqtrade   # watch startup
docker compose logs -f telegram-ui # watch bot connect
```

---

## Verification

```bash
# API health
curl http://127.0.0.1:8080/api/v1/ping
# Expected: {"status":"pong"}

# Check containers
docker compose ps

# View logs
docker compose logs -f --tail 100 freqtrade
docker compose logs -f --tail 100 telegram-ui
```

---

## Configuration

### Environment Variables

Loaded from `.env` in the project directory:
- `BINGX_API_KEY` / `BINGX_API_SECRET` — exchange credentials
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` — bot credentials
- `STEPFUN_API_KEY` — AI sentiment (optional)
- `TZ=Asia/Singapore` — timezone

**Edit `.env` before first run.**

### Freqtrade Config

- `configs/config.json` — main config (strategy, risk, pairs)
- `configs/config.local.json` — secrets override (ignored by git)

Strategy: `Claw5MHybrid` (MTF surgical scalper) — hardcoded in `docker-compose.yml` CMD.

---

## Volume Persistence

| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `./user_data` | `/app/user_data` | Dry-run SQLite DB, logs, hyperopt results |
| `./configs` | `/app/configs` | Config files (read-only) |
| `./strategies` | `/app/strategies` | Strategy code (read-only) |
| `./clawforge` | `/app/clawforge` | Telegram UI code (read-only) |
| `./generated` | `/app/generated` | PnL cards, images |

**`user_data/` persists across container rebuilds** — your mock trade history is safe.

---

## Commands

```bash
# Start
docker compose up -d

# Stop (keeps volumes)
docker compose down

# Stop + remove volumes (WARNING: wipes dry-run DB)
docker compose down -v

# Restart
docker compose restart freqtrade
docker compose restart telegram-ui

# View logs
docker compose logs -f freqtrade
docker compose logs -f telegram-ui

# Exec into container (debug)
docker compose exec freqtrade bash
docker compose exec telegram-ui bash

# Rebuild after code changes (not needed for code mounts — just restart service)
docker compose build --no-cache

# Stop old non-Docker processes (if any)
pkill -f "freqtrade"
pkill -f "clawforge.telegram_ui"
```

---

## Network

Containers communicate via internal DNS:
- `telegram-ui` → Freqtrade API at `http://freqtrade:8080`
- Host → Freqtrade API at `http://127.0.0.1:8080`

**Do not expose port 8080 publicly** — API has no auth on localhost. If you need external access, set up Traefik reverse proxy with basic auth.

---

## Troubleshooting

### Freqtrade crashes on startup
```bash
docker compose logs freqtrade | tail -50
```
Common causes:
- Missing `.env` file — copy from `.env.example`
- `user_data/` permissions — `chown -R 1000:1000 user_data/` (or just delete to regenerate)
- Port 8080 already in use — change `ports:` mapping

### Telegram UI can't connect to API
- Check `docker compose logs telegram-ui`
- Ensure `freqtrade` healthcheck passed: `docker compose ps`
- Verify `FREQTRADE_API_URL` in `.env` or compose file (should be `http://freqtrade:8080` inside Docker network)

### No 1H/4H data
- BingX may not provide those intervals — check logs for `No data found`
- Strategy will still run but MTF filters may be neutral
- Consider adding Binance fallback for higher TFs (code already has fallback logic)

### Data warnings (pandas FutureWarning)
Harmless — can be ignored. Suppress by updating pandas-ta or adding `warnings.filterwarnings("ignore")`.

---

## Updating Code

Since code is **bind-mounted**, you can edit files directly on host:
```bash
nano strategies/claw5m_hybrid.py  # edit strategy
# Changes take effect after Freqtrade restart:
docker compose restart freqtrade
```

No need to rebuild image for code changes. Rebuild only if you modify `requirements.txt` or `Dockerfile`.

---

## Logs Location

- Container logs: `docker compose logs -f [service]`
- Host-mounted logs (if you bind-mounted `user_data/logs`):
  - `./user_data/logs/freqtrade.log`
  - `./user_data/logs/telegram_ui.log`

---

## Removing the Stack

```bash
# Stop and remove containers (keeps volumes)
docker compose down

# Stop + remove everything including volumes (WARNING: data loss)
docker compose down -v

# Remove images
docker compose build --no-cache  # rebuild fresh
```

---

## Security Notes

- **API is localhost-only** (`127.0.0.1:8080`). Not exposed to internet.
- **Telegram bot token** stored in `.env` — keep secret.
- **JWT secret** in `config.json` is default — change for production.
- **No auth** on Freqtrade API by default. If you expose it, enable `--api_username`/`--api_password` in config.

---

## Next Steps

1. ✅ Build & start stack
2. ✅ Verify API `pong`
3. ✅ Check Telegram bot connected (startup message)
4. ✅ Wait for next session (Monday NY 21:30 SGT) — observe MTF trades
5. ✅ Monitor logs for `1h_trend_strength` and `macro_bias` decisions

**Questions?** Check `logs/` or run `docker compose logs -f [service]`.
