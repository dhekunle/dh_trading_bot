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


## DH Binary Trader: site layout
- `/` public home page, `/signup` and `/login` for members
- `/app` member dashboard: signals drop in live with entry countdown and alerts
- `/admin` owner area (needs ADMIN_USERNAME and ADMIN_PASSWORD): bot controls at `/admin/patience` and `/admin/3min`, members at `/admin/users`
- `/health` for UptimeRobot
- Members only see a signal after you tap ACTIVATE. Telegram posting still works as before.
- Set DATABASE_URL to a hosted Postgres database. SQLite files are wiped when Render redeploys or restarts.

## Members, chat and Telegram pictures
- Sign up asks for full name, username and email. Members log in with email or username. Older accounts are asked to add a name and username the first time they log in.
- Community chat on the member dashboard. Members chat with each other and the admin. Links are blocked for members, messages are rate limited, and the admin can delete messages or mute a member at `/admin/chat` and `/admin/users`.
- Pausing a bot sends the SESSION CLOSE picture to that bot's Telegram group. Resuming sends SESSION START. The pictures are in `app/assets/stickers/`.
- New database columns and the `chat_messages` table are created automatically on startup. On Supabase, also run: `alter table chat_messages enable row level security;`
