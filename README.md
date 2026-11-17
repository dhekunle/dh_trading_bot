# Forex Signal Bot - Website + Telegram

Modular trading signal bot converted from Telegram-only to a full web dashboard + Telegram.

## Features
- Yahoo Finance prices (cached and shared by both bots, with rate limit protection)
- All original filters (choppiness, session quality, news, M5/M15, ADX, etc.)
- Groq HIGH-confidence confirmation
- Home page with Patience Bot and 3 min Bot
- Patience Bot: session filters, high quality signals
- 3 min Bot: high volatility mode, 2 martingale levels, next signal 3 minutes after the previous result
- Dashboard for each bot with ACTIVATE / SKIP / WIN / LOSS, stats, pause, auto scan and a live scan status line
- /status shows price data health and why a bot is not signalling
- SQLite database
- Protections: blacklists, cooldowns, consecutive loss pause

## Setup

1. Copy `.env.example` to `.env` and fill in your keys:
   ```bash
   cp .env.example .env
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. Open dashboard: http://localhost:8000

## Notes
- Rotate any keys that were previously exposed.
- A signal is only posted to Telegram after you tap ACTIVATE. Unactivated signals expire after 10 minutes.
- Only one open signal per bot at a time. Log its result to unlock the next scan.
- The scanner runs in the background once started from the dashboard.
