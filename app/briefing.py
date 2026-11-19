"""
Morning briefing: today's news and what it could mean for the day.

Built from the economic calendar (the same feed the news filter uses) plus a few
public headlines. Groq writes the analysis. If Groq is unavailable the briefing
falls back to a plain calendar summary, so something useful is always sent.
Sent only to the admin's personal Telegram chat, never to the group.
"""
import datetime
import os
import re
import xml.etree.ElementTree as ET
from typing import List, Optional, Tuple

import requests

from .engine_core import PAIRS, WAT, get_calendar_events

# Optional override: NEWS_RSS_URLS="https://a/rss,https://b/rss"
DEFAULT_FEEDS = ("https://www.fxstreet.com/rss/news", "https://finance.yahoo.com/news/rssindex")
FEEDS = [u.strip() for u in os.getenv("NEWS_RSS_URLS", ",".join(DEFAULT_FEEDS)).split(",") if u.strip()]
MODEL = "openai/gpt-oss-20b"
MAX_HEADLINES = 12
IMPACT_RANK = {"high": 2, "medium": 1}
MAX_TELEGRAM_CHARS = 3900

_cache = {"date": None, "body": None, "note": ""}


# ------------------------------------------------------------------ data
def todays_events(now: Optional[datetime.datetime] = None) -> List[dict]:
    """High and medium impact events that fall on today's date in WAT."""
    now = now or datetime.datetime.now(WAT)
    out = []
    for e in get_calendar_events() or []:
        try:
            impact = (e.get("impact") or "").lower()
            if impact not in IMPACT_RANK:
                continue
            when = datetime.datetime.strptime(e["date"], "%Y-%m-%dT%H:%M:%S%z").astimezone(WAT)
            if when.date() != now.date():
                continue
            out.append({
                "when": when, "time": when.strftime("%I:%M %p"),
                "ccy": (e.get("country") or "").upper(), "title": e.get("title") or "Event",
                "impact": impact, "forecast": e.get("forecast") or "", "previous": e.get("previous") or "",
            })
        except Exception:
            continue
    out.sort(key=lambda x: x["when"])
    return out


def fetch_headlines() -> List[str]:
    """Latest headline titles from public RSS feeds. Best effort: failures are skipped."""
    titles, seen = [], set()
    for url in FEEDS:
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r.status_code != 200 or len(r.content) > 1_500_000:
                continue
            root = ET.fromstring(r.content)
            for item in root.iter("item"):
                title = " ".join((item.findtext("title") or "").split())
                key = title.lower()
                if title and key not in seen:
                    seen.add(key)
                    titles.append(title[:160])
                if len(titles) >= MAX_HEADLINES:
                    return titles
        except Exception as e:
            print(f"[BRIEFING] feed {url} failed: {str(e)[:100]}")
    return titles


def pair_notes(events: List[dict]) -> Tuple[dict, List[str]]:
    """(pair -> high impact times that touch it, pairs with no medium/high news at all today)."""
    risky = {}
    for e in events:
        if e["impact"] != "high":
            continue
        for pair in PAIRS:
            if e["ccy"] in pair.split("/"):
                risky.setdefault(pair, []).append(f"{e['time']} ({e['ccy']})")
    busy = {e["ccy"] for e in events}
    calm = [p for p in PAIRS if not (set(p.split("/")) & busy)]
    return risky, calm


def _event_line(e: dict) -> str:
    extra = []
    if e["forecast"]:
        extra.append(f"forecast {e['forecast']}")
    if e["previous"]:
        extra.append(f"previous {e['previous']}")
    tail = f" ({', '.join(extra)})" if extra else ""
    return f"{e['time']} WAT | {e['ccy']} | {e['impact'].upper()} | {e['title']}{tail}"


# ------------------------------------------------------------------ writing
def build_prompt(now, events, headlines, risky, calm) -> str:
    ev = "\n".join(_event_line(e) for e in events) or "No high or medium impact events on today's calendar."
    hl = "\n".join(f"- {h}" for h in headlines) or "No headlines could be loaded."
    risk = "\n".join(f"{p}: {', '.join(t)}" for p, t in risky.items()) or "None"
    return f"""You are the morning analyst for a forex binary options signal service. Today is {now.strftime('%A %d %B %Y')} (WAT, Africa/Lagos time).
Trading sessions in WAT: Tokyo 01:00-09:00, London 09:00-17:00, New York 14:00-22:00. Best hours: Tokyo 02:00-05:00 and early London 09:00-12:00.
The bot trades 1 to 5 minute expiries on these pairs: {', '.join(PAIRS)}.

TODAY'S ECONOMIC CALENDAR (WAT):
{ev}

PAIRS TOUCHED BY HIGH IMPACT NEWS (and when):
{risk}

PAIRS WITH NO MEDIUM OR HIGH NEWS TODAY: {', '.join(calm) or 'None'}

LATEST HEADLINES:
{hl}

Write a short morning briefing in PLAIN TEXT for the trader. No markdown: no asterisks, no hashtags, no tables. Use these emojis as section markers and keep the whole thing under 1500 characters:
🌍 Mood of the day: one line, Good, Mixed or Risky, with a short reason.
📰 News that matters: up to 4 items. For each, say if it looks good or bad for trading and how it could move the currency, using wording like could or may. Mention the time in WAT.
✅ Good pairs to trade today: 3 to 5 pairs with a very short reason each. Prefer pairs from the no-news list.
🚫 Be careful with: pairs and the time windows around high impact news.
🕒 Best time windows today (WAT).
Rules: use ONLY the information above, do not invent events, numbers or prices, and never promise a result. If the data is thin, say so honestly."""


def _fallback(now, events, risky, calm, reason: str) -> str:
    lines = ["🗞 Events today (WAT)"]
    lines += [f"• {_event_line(e)}" for e in events[:12]] or ["• No high or medium impact events today."]
    if risky:
        lines += ["", "⚠️ Be careful with these pairs around high impact news:"]
        lines += [f"• {p}: {', '.join(t)}" for p, t in list(risky.items())[:10]]
    if calm:
        lines += ["", "✅ Calmer pairs today (no medium or high news): " + ", ".join(calm[:8])]
    lines += ["", f"ℹ️ Calendar-only summary. AI analysis unavailable ({reason})."]
    return "\n".join(lines)


def ask_ai(engine, prompt: str) -> Tuple[Optional[str], str]:
    """Returns (text, reason_if_failed)."""
    client = getattr(engine, "groq_client", None)
    if client is None:
        return None, "Groq key missing"
    blocked = getattr(engine, "groq_blocked_until", None)
    if blocked and datetime.datetime.now() < blocked:
        return None, "Groq limit reached"
    try:
        resp = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": prompt}],
            reasoning_effort="low", max_completion_tokens=3000,
        )
        text = (resp.choices[0].message.content or "").strip()
        text = re.sub(r"[*#`_]{1,}", "", text)          # keep it plain for Telegram
        return (text or None), ("" if text else "empty reply")
    except Exception as e:
        return None, str(e)[:80]


def get_briefing(engine, force: bool = False) -> Tuple[str, str]:
    """Returns (message body, note). One briefing is built per day and reused by both bots."""
    now = datetime.datetime.now(WAT)
    if not force and _cache["date"] == now.date() and _cache["body"]:
        return _cache["body"], _cache["note"]
    events = todays_events(now)
    headlines = fetch_headlines()
    risky, calm = pair_notes(events)
    text, reason = ask_ai(engine, build_prompt(now, events, headlines, risky, calm))
    if text:
        body, note = text, "AI analysis"
    else:
        body, note = _fallback(now, events, risky, calm, reason or "unknown"), f"calendar only ({reason})"
    _cache.update(date=now.date(), body=body, note=note)
    return body, note


def compose(engine_name: str, body: str) -> str:
    now = datetime.datetime.now(WAT)
    head = (f"🌅 MORNING BRIEFING · {engine_name}\n"
            f"📅 {now.strftime('%A, %d %b %Y')} · {now.strftime('%I:%M %p')} WAT\n\n")
    foot = "\n\nℹ️ Information only, not a guarantee. Signals still go through all the bot filters."
    return (head + body)[:MAX_TELEGRAM_CHARS - len(foot)] + foot
