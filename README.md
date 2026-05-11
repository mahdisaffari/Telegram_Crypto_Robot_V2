# Persian Crypto Arbitrage Telegram Bot

An asynchronous Telegram bot (Python) that fetches spot prices for whitelisted coins from several Iranian exchanges, compares them in **Toman**, and reports arbitrage spread and best buy/sell venues. User-facing messages are in **Persian (Farsi)**; each reported price is shown as **plain digits** (0–9 and an optional decimal point) derived from the exchange data via `Decimal` (no `float` conversion for display, no thousands separators).

> **Note:** This project was created with the help of **AI-assisted development tools** (e.g. coding assistants). Review security-sensitive parts (tokens, deployment, and exchange integrations) before production use.

---

## Features

- **Coins:** `USDT`, `USDC`, `DAI`, `BTC`, `ETH`, `TRX`, `XRP`, `XLM`, `LTC`, `SOL`, `MATIC`, plus `USDC-TRC20` / `USDC-BEP20` style aliases (all resolve to the same `USDC` IRT book where the exchange has a single market)
- **Exchanges (public APIs only):** Nobitex, Bitpin, Ramzinex, Exir, Wallex, Sarrafex (SarrafEx), Tabdeal (تبدیل), Aban Tether (آبان‌تتر)
- **Stack:** [aiogram](https://docs.aiogram.dev/) v3.x, [aiohttp](https://docs.aiohttp.org/), `asyncio.gather()` for concurrent requests
- **Resilience:** isolated `try/except` per exchange; partial failures do not stop the bot

### Exchange APIs used for prices (reference)

| Venue | How spot price is read |
|-------|-------------------------|
| **Tabdeal** (تبدیل) | Public order book: `GET https://api1.tabdeal.org/r/api/v1/depth?symbol={COIN}IRT` — [docs.tabdeal.org](https://docs.tabdeal.org) |
| **Aban Tether** (آبان‌تتر) | Public OTC ticker: `GET https://api.abantether.com/api/v1/manager/otc/ticker` — [docs.abantether.com](https://docs.abantether.com) |
| **OK Exchange** (اوکی‌اکسچنج) | Official REST/WebSocket documentation: [docs.ok-ex.io](https://docs.ok-ex.io). A stable **anonymous** REST host/path was not verified from here; integrate using the hostname and paths from your OK Exchange developer/API settings when available. |
| **Iranicard** (ایرانیکارت) | No public developer ticker/API for IRT spot was found in open documentation; the site focuses on USD/global reference prices. |

---

## Requirements

- **Python 3.11 or 3.12** (recommended for stable `aiohttp` wheels; very new Python versions may lack wheels)
- A **Telegram Bot token** from [@BotFather](https://t.me/BotFather)
- Outbound **HTTPS** access to `api.telegram.org` and the exchange endpoints (use a VPN or proxy if your region blocks them)

---

## Local setup

```bash
git clone <your-repo-url> Soheil_crypto_bot
cd Soheil_crypto_bot
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set BOT_TOKEN
python main.py
```

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | **Yes** | Telegram bot token |
| `STICKER_FILE_ID` | No | Optional sticker sent before each report |
| `REQUEST_TIMEOUT_S` | No | Per-request timeout in seconds (5–120, default 14) |

---

## Deploy on a Linux server (Docker — recommended)

### 1. Install Docker and Compose plugin

Follow your distribution’s documentation for Docker Engine and Compose v2.

### 2. Deploy

```bash
cd /opt   # or any directory you prefer
git clone <your-repo-url> Soheil_crypto_bot
cd Soheil_crypto_bot
cp .env.example .env
nano .env   # set BOT_TOKEN (and optional vars)
docker compose up -d --build
```

### 3. Logs and lifecycle

```bash
docker compose logs -f
docker compose restart
docker compose down
```

The container runs `python -u main.py` (unbuffered stdout for logging).

---

## Deploy without Docker (systemd)

1. Create venv and install dependencies on the server (same as local setup).
2. Place the project (e.g.) under `/opt/Soheil_crypto_bot` with a `.env` file.
3. Adapt and install the example unit:

```bash
sudo cp deploy/arbitrage-bot.service.example /etc/systemd/system/arbitrage-bot.service
sudo nano /etc/systemd/system/arbitrage-bot.service
sudo systemctl daemon-reload
sudo systemctl enable --now arbitrage-bot
sudo journalctl -u arbitrage-bot -f
```

---

## Project layout

```
Soheil_crypto_bot/
├── main.py                 # Entry point (sets PYTHONPATH for src/)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── deploy/
│   └── arbitrage-bot.service.example
└── src/
    └── arbitrage_bot/      # Application package
```

---

## Troubleshooting

- **`Cannot connect to api.telegram.org`:** network or firewall blocking Telegram; configure VPN/proxy at OS or Docker level.
- **`BOT_TOKEN is missing`:** ensure `.env` exists next to `docker-compose.yml` (Compose `env_file`) or is loaded in systemd `EnvironmentFile`.
- **`pip` / `aiohttp` install errors:** switch to Python 3.12 and use a fresh venv.

---

## Security

- Never commit `.env` or real tokens (`.gitignore` excludes `.env`).
- Rotate tokens if they are exposed.
- Prefer a non-root user in systemd and minimal container privileges.


