# Forex Signal Bot - Website + Telegram

Modular trading signal bot converted from Telegram-only to a full web dashboard + Telegram.

## Features
- Twelve Data for market data
- All original filters (choppiness, session quality, news, M5/M15, ADX, etc.)
- Groq HIGH-confidence confirmation
- Web dashboard only (no Telegram required)
- Preview signals, activate them, log WIN/LOSS, view stats, pause/resume
- All original filters and protections
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
- Start with Twelve Data Grow plan ($29/mo recommended).
- The scanner runs in the background once started from the dashboard.
