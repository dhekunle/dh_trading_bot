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
- Pausing a bot posts a SESSION CLOSED text message (with emoji) in that bot's Telegram group. Resuming posts SESSION STARTED.
- Skipping a signal deletes it from the Telegram group and posts a SKIP message.
- Each bot keeps its own results, win rate and trade numbering (Patience and 3 min both start at #1).
- New database columns and the `chat_messages` table are created automatically on startup. On Supabase, also run: `alter table chat_messages enable row level security;`

## Profile pictures and private messages
- Members add a profile picture at `/app/settings` (Profile button on the dashboard). The photo is cropped and shrunk to 256px in the browser, then stored in the database, so it survives redeploys. Pictures show in the community chat and private messages. Members without one get a coloured circle with their first letter.
- Private messages: the dashboard has a Private messages card. Members search by username, or tap a name in the community chat, to start a 1 to 1 chat. Unread messages show a red badge. Links are blocked, messages are rate limited, and a member muted by the admin cannot send private messages either. The admin session has no private inbox and cannot read member messages.
- New columns (`users.avatar`, `users.avatar_v`) and the `direct_messages` table are created automatically on startup. On Supabase, also run: `alter table direct_messages enable row level security;`

## Morning briefing (personal chat only)
- When you tap Resume on a bot for the first time each day, the bot reads today's economic calendar plus a few public headlines. Groq then writes a short briefing: mood of the day, news that matters (good or bad), good pairs to trade, pairs to be careful with, and the best time windows in WAT.
- It is sent to your personal chat only (`MY_PERSONAL_CHAT_ID`, or `MY_PERSONAL_CHAT_ID_3MIN` for the 3 min Bot), never the group.
- If Groq is unavailable you still get a calendar-only summary. Resuming again the same day does not repeat it; use the Send briefing button on the bot dashboard to send it again.
- Optional: set `NEWS_RSS_URLS` to a comma separated list of RSS feeds to change the headline sources.
