import os
import html as htmllib
import threading
from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import datetime
import pytz
import asyncio
from .database import init_db, get_db, SessionLocal, Trade, Stats
from .signal_engine import SignalEngine
from .signal_engine_3min import SignalEngine3Min
from .engine_core import news_status, SKIP_BAN_MINUTES
from . import yf_data
import requests
from .config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_TOKEN_3MIN,
    TELEGRAM_CHAT_ID, TELEGRAM_CHAT_ID_3MIN,
    MY_PERSONAL_CHAT_ID, MY_PERSONAL_CHAT_ID_3MIN
)

app = FastAPI(title="Patience Bot & 3 min Bot")

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

init_db()
patience_engine = SignalEngine()
three_min_engine = SignalEngine3Min()
WAT = pytz.timezone("Africa/Lagos")

# State
bot_paused_patience = False
bot_paused_3min = False
scanning_patience = False
scanning_3min = False
auto_scan_patience = True
auto_scan_3min = True
last_3min_result_time = None
three_min_martingale_level = 0  # 0, 1, or 2

ENGINES = {"patience": patience_engine, "3min": three_min_engine}
scan_locks = {"patience": threading.Lock(), "3min": threading.Lock()}
news_warned = {"patience": False, "3min": False}
PENDING_EXPIRE_MINUTES = 10

def get_token_and_chat(market_type: str):
    if market_type == "3min":
        return TELEGRAM_BOT_TOKEN_3MIN or TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID_3MIN or TELEGRAM_CHAT_ID, MY_PERSONAL_CHAT_ID_3MIN or MY_PERSONAL_CHAT_ID
    return TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, MY_PERSONAL_CHAT_ID

def send_telegram(text: str, token: str, chat_id: str):
    """Send a message using the given bot token and chat ID."""
    if not token or not chat_id:
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"Telegram send error: {e}")

def build_signal_message(trade: Trade) -> str:
    """Group message in the same format as the original bots."""
    engine = ENGINES.get(trade.market_type, patience_engine)
    sessions, quality, _ = engine.get_session_quality()
    session_text = ", ".join(sessions) if sessions else "No active session"
    vol_tag = "\nSTRICT MODE - High Volatility" if getattr(engine, "high_volatility_mode", False) else ""
    now = datetime.datetime.now(WAT)
    entry = now + datetime.timedelta(minutes=1)
    expire = entry + datetime.timedelta(minutes=trade.expiry_mins)
    mart_entry = expire + datetime.timedelta(minutes=1)
    mart_expire = mart_entry + datetime.timedelta(minutes=trade.expiry_mins)
    plural = "s" if trade.expiry_mins > 1 else ""
    mg = f" (Martingale {trade.martingale_level})" if trade.martingale_level else ""
    return (
        f"{now.strftime('%Y-%m-%d %H:%M WAT')}\n{session_text}\n"
        f"Session Quality: {quality}{vol_tag}\n\n"
        f"SIGNAL Trade #{trade.trade_number}{mg}\n---------------------\n"
        f"Asset:     {trade.asset}\nAction:    {trade.action}\n---------------------\n"
        f"Entry Time:  {entry.strftime('%I:%M %p WAT')}\n"
        f"Expiry Time: {expire.strftime('%I:%M %p WAT')}\n"
        f"Duration:    {trade.expiry_mins} Minute{plural}\n---------------------\n"
        f"Optional Martingale if LOSS:\n"
        f"Entry Time:  {mart_entry.strftime('%I:%M %p WAT')}\n"
        f"Expiry Time: {mart_expire.strftime('%I:%M %p WAT')}\n"
        f"Duration:    {trade.expiry_mins} Minute{plural}\n"
        f"Stake:       DOUBLE previous stake\n---------------------"
    )

STYLE = '''
<style>
:root { --bg: #0f1117; --card: #1a1d27; --text: #e4e6eb; --accent: #3b82f6; --green: #22c55e; --red: #ef4444; }
body { font-family: system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }
.container { max-width: 1100px; margin: 0 auto; }
h1 { margin-bottom: 8px; }
.card { background: var(--card); border-radius: 12px; padding: 20px; margin-bottom: 16px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.btn { background: var(--accent); color: white; border: none; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-weight: 600; text-decoration: none; display: inline-block; }
.btn:hover { opacity: 0.9; }
.btn-green { background: var(--green); }
.btn-red { background: var(--red); }
.btn-gray { background: #4b5563; }
.btn-3min { background: #8b5cf6; }
.status { font-size: 0.9em; color: #9ca3af; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 8px; border-bottom: 1px solid #2d313c; }
.pending { color: #fbbf24; }
.skipped, .expired { color: #9ca3af; }
.win { color: var(--green); }
.loss { color: var(--red); }
.home-options { display: flex; gap: 24px; justify-content: center; margin-top: 60px; flex-wrap: wrap; }
.home-card { background: var(--card); border-radius: 16px; padding: 40px; width: 300px; text-align: center; }
.home-card h2 { margin-top: 0; }
</style>
'''

@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    return {"status": "ok"}

@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def home():
    html = f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Signal Bots</title>{STYLE}</head>
<body><div class="container">
    <h1 style="text-align:center; margin-top:40px;">Forex Signal Bots</h1>
    <p class="status" style="text-align:center;">Choose your bot</p>
    <div class="home-options">
        <div class="home-card">
            <h2>Patience Bot</h2>
            <p>High-quality real-market signals with session filters. Selective and patient.</p>
            <a href="/patience" class="btn">Enter Patience Bot</a>
        </div>
        <div class="home-card">
            <h2>3 min Bot</h2>
            <p>Full volatility logic, 2 martingale levels, expiry 2–5 min. Next signal 3 minutes after previous result.</p>
            <a href="/3min" class="btn btn-3min">Enter 3 min Bot</a>
        </div>
    </div>
</div></body></html>'''
    return HTMLResponse(html)

def build_dashboard(market: str, db: Session, paused: bool, auto_on: bool, quality_info=None, engine=None):
    trades = db.query(Trade).filter(Trade.market_type == market).order_by(Trade.id.desc()).limit(15).all()
    stats = db.query(Stats).order_by(Stats.id.desc()).first()
    
    stats_html = "<p>No stats yet</p>"
    if stats:
        stats_html = f"<p>Wins: {stats.wins or 0} · Losses: {stats.losses or 0} · Draws: {stats.draws or 0}</p><p>Next Trade #: {stats.trade_number or 1}</p>"
    
    rows = ""
    for t in trades:
        status = t.status or "pending"
        mg = f" (MG{t.martingale_level})" if t.martingale_level else ""
        actions = ""
        if status == "pending":
            actions += f'<form action="/post/{t.id}" method="post" style="display:inline;"><button class="btn btn-green" style="padding:6px 12px;font-size:0.85em;">ACTIVATE</button></form> <form action="/skip/{t.id}" method="post" style="display:inline;"><button class="btn btn-gray" style="padding:6px 12px;font-size:0.85em;">SKIP</button></form> '
        if status in ["pending", "active"]:
            actions += f'''
            <form action="/result/{t.id}" method="post" style="display:inline;"><input type="hidden" name="result" value="WIN"><button class="btn btn-green" style="padding:6px 10px;font-size:0.8em;">W</button></form>
            <form action="/result/{t.id}" method="post" style="display:inline;"><input type="hidden" name="result" value="LOSS"><button class="btn btn-red" style="padding:6px 10px;font-size:0.8em;">L</button></form>
            '''
        rows += f'''
        <tr>
            <td>{t.trade_number}{mg}</td>
            <td>{t.asset}</td>
            <td>{t.action}</td>
            <td>{t.expiry_mins}m</td>
            <td class="{status}">{status.upper()}</td>
            <td>{actions}</td>
        </tr>
        '''
    
    pause_label = "Resume" if paused else "Pause"
    bot_status = "PAUSED" if paused else "ACTIVE"
    auto_status = "ON" if auto_on else "OFF"
    now = datetime.datetime.now(WAT).strftime("%Y-%m-%d %H:%M WAT")
    title = "Patience Bot" if market == "patience" else "3 min Bot"
    back = '<a href="/" class="status">← Home</a>'
    
    q_info = ""
    if quality_info:
        sessions, quality, reason = quality_info
        q_info = f" · Session: {', '.join(sessions) if sessions else 'None'} · Quality: <strong>{quality}</strong> ({reason})"
    
    vol_tag = ""
    if engine is not None and getattr(engine, "high_volatility_mode", False):
        vol_tag = " · STRICT MODE (High Volatility)"
    
    scan_line = ""
    if engine is not None:
        when = engine.last_scan_at.strftime("%H:%M:%S") if engine.last_scan_at else "never"
        groq_state = "Groq OK" if engine.groq_configured else "Groq key missing"
        scan_line = htmllib.escape(f"Last scan {when}: {engine.last_scan_info} · {yf_data.summary()} · {groq_state}")

    html = f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="refresh" content="30"><title>{title}</title>{STYLE}</head>
<body><div class="container">
    <h1>{title} {back}</h1>
    <p class="status">{now}{q_info}{vol_tag} · Auto-scan: {auto_status}</p>
    <p class="status">{scan_line}</p>
    <div class="grid">
        <div class="card">
            <h3>Controls</h3>
            <form action="/scan/{market}" method="post" style="display:inline;">
                <button class="btn" {"disabled" if paused else ""}>Scan Now</button>
            </form>
            <form action="/pause/{market}" method="post" style="display:inline; margin-left:8px;">
                <button class="btn btn-gray">{pause_label}</button>
            </form>
            <form action="/toggle-auto/{market}" method="post" style="display:inline; margin-left:8px;">
                <button class="btn btn-gray">Auto: {auto_status}</button>
            </form>
            <p class="status" style="margin-top:12px;">Bot is {bot_status}</p>
        </div>
        <div class="card">
            <h3>Stats</h3>
            {stats_html}
        </div>
    </div>
    <div class="card">
        <h3>Recent Signals</h3>
        <table>
            <tr><th>#</th><th>Asset</th><th>Action</th><th>Expiry</th><th>Status</th><th>Actions</th></tr>
            {rows if rows else "<tr><td colspan='6'>No signals yet</td></tr>"}
        </table>
    </div>
</div></body></html>'''
    return html

@app.get("/patience", response_class=HTMLResponse)
async def patience_dashboard(db: Session = Depends(get_db)):
    sessions, quality, reason = patience_engine.get_session_quality()
    html = build_dashboard("patience", db, bot_paused_patience, auto_scan_patience, (sessions, quality, reason), patience_engine)
    return HTMLResponse(html)

@app.get("/3min", response_class=HTMLResponse)
async def three_min_dashboard(db: Session = Depends(get_db)):
    sessions, quality, reason = three_min_engine.get_session_quality()
    html = build_dashboard("3min", db, bot_paused_3min, auto_scan_3min, (sessions, quality, reason), three_min_engine)
    return HTMLResponse(html)

@app.post("/scan/{market}")
async def start_scan(market: str):
    m = "patience" if market == "patience" else "3min"
    ENGINES[m].set_info("Scanning now...")
    # Run in a worker thread so the website stays responsive while prices download
    asyncio.get_running_loop().run_in_executor(None, scan_market, m)
    return RedirectResponse(f"/{m}", status_code=303)

@app.post("/skip/{trade_id}")
async def skip_signal(trade_id: int, db: Session = Depends(get_db)):
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade or trade.status != "pending":
        return RedirectResponse("/", status_code=303)
    trade.status = "skipped"
    db.commit()
    engine = ENGINES.get(trade.market_type, patience_engine)
    engine.skip_pair(trade.asset)
    engine.set_info(f"{trade.asset} skipped and banned for {SKIP_BAN_MINUTES} min. Scanning again.")
    return RedirectResponse("/3min" if trade.market_type == "3min" else "/patience", status_code=303)

@app.post("/post/{trade_id}")
async def post_signal(trade_id: int, db: Session = Depends(get_db)):
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade or trade.status != "pending":
        return RedirectResponse("/", status_code=303)
    trade.status = "active"
    db.commit()
    # Post to the correct Telegram group using the correct token
    token, chat_id, personal_id = get_token_and_chat(trade.market_type)
    send_telegram(build_signal_message(trade), token, chat_id)
    if personal_id:
        send_telegram(f"Activated: {trade.asset} {trade.action}", token, personal_id)
    redir = "/3min" if trade.market_type == "3min" else "/patience"
    return RedirectResponse(redir, status_code=303)

@app.post("/result/{trade_id}")
async def log_result(trade_id: int, result: str = Form(...), db: Session = Depends(get_db)):
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    result = (result or "").upper()
    if not trade or trade.result or result not in ("WIN", "LOSS", "DRAW"):
        return RedirectResponse("/", status_code=303)
    trade.result = result
    trade.status = result.lower()
    trade.resolved_at = datetime.datetime.utcnow()
    db.commit()

    stats = db.query(Stats).order_by(Stats.id.desc()).first()
    if not stats:
        stats = Stats(week=datetime.datetime.now(WAT).strftime("%Y-W%W"), wins=0, losses=0, draws=0,
                      martingale_wins=0, martingale_losses=0, total=0, trade_number=1)
        db.add(stats)
    if result == "WIN":
        stats.wins = (stats.wins or 0) + 1
    elif result == "LOSS":
        stats.losses = (stats.losses or 0) + 1
    elif result == "DRAW":
        stats.draws = (stats.draws or 0) + 1
    stats.total = (stats.total or 0) + 1
    stats.trade_number = trade.trade_number + 1
    db.commit()

    # Post result to the correct Telegram group
    result_msg = f"Trade #{trade.trade_number} - {result}!\n{trade.asset} {trade.action}"
    token, chat_id, personal_id = get_token_and_chat(trade.market_type)
    send_telegram(result_msg, token, chat_id)
    if personal_id:
        send_telegram(result_msg, token, personal_id)

    # Protections: win cooldown, loss blacklist, pause after consecutive losses
    engine = ENGINES.get(trade.market_type, patience_engine)
    cooldown_msg = engine.register_result(trade.asset, result)
    if cooldown_msg:
        send_telegram(cooldown_msg, token, chat_id)
        if personal_id:
            send_telegram(cooldown_msg, token, personal_id)

    if trade.market_type == "3min":
        global last_3min_result_time, three_min_martingale_level
        last_3min_result_time = datetime.datetime.utcnow()
        if result == "LOSS":
            three_min_martingale_level = min(three_min_martingale_level + 1, 2)
        else:
            three_min_martingale_level = 0

    redir = "/3min" if trade.market_type == "3min" else "/patience"
    return RedirectResponse(redir, status_code=303)

@app.post("/pause/{market}")
async def toggle_pause(market: str):
    global bot_paused_patience, bot_paused_3min
    if market == "patience":
        bot_paused_patience = not bot_paused_patience
        return RedirectResponse("/patience", status_code=303)
    else:
        bot_paused_3min = not bot_paused_3min
        return RedirectResponse("/3min", status_code=303)

@app.post("/toggle-auto/{market}")
async def toggle_auto(market: str):
    global auto_scan_patience, auto_scan_3min
    if market == "patience":
        auto_scan_patience = not auto_scan_patience
        return RedirectResponse("/patience", status_code=303)
    else:
        auto_scan_3min = not auto_scan_3min
        return RedirectResponse("/3min", status_code=303)

def scan_market(market: str):
    """Scan one bot once. Blocking, so it always runs in a worker thread."""
    engine = ENGINES[market]
    lock = scan_locks[market]
    if not lock.acquire(blocking=False):
        return  # a scan for this bot is already running
    try:
        paused = bot_paused_patience if market == "patience" else bot_paused_3min
        if paused:
            engine.set_info("Bot is paused")
            return

        left = engine.cooldown_remaining()
        if left:
            engine.set_info(f"Cooling down after consecutive losses, {left // 60 + 1} min left")
            return

        sessions, quality, reason = engine.get_session_quality()
        if not sessions or quality in ("AVOID", "CLOSED"):
            engine.set_info(f"Not scanning: {reason}")
            return

        token, chat_id, personal_id = get_token_and_chat(market)

        safe, news_list, safe_time = news_status()
        if not safe:
            safe_str = safe_time.astimezone(WAT).strftime("%I:%M %p WAT")
            engine.set_info(f"Paused for high impact news until {safe_str}")
            if not news_warned[market]:
                news_warned[market] = True
                lines = [f"{n['country']} - {n['title']} at {n['time_str']}" for n in news_list]
                send_telegram("TRADING PAUSED - HIGH IMPACT NEWS!\n" + "\n".join(lines) + f"\n\nResume at: {safe_str}", token, chat_id)
                if personal_id:
                    send_telegram(f"News! Signals paused.\nSafe after: {safe_str}", token, personal_id)
            return
        if news_warned[market]:
            news_warned[market] = False
            send_telegram("News over! Signals resuming...", token, chat_id)
            if personal_id:
                send_telegram("Safe to trade!", token, personal_id)

        if market == "3min":
            if last_3min_result_time is not None:
                wait = 180 - (datetime.datetime.utcnow() - last_3min_result_time).total_seconds()
                if wait > 0:
                    engine.set_info(f"Next signal allowed {int(wait)}s after the last result")
                    return
            engine.check_volatility()

        db = SessionLocal()
        try:
            # A signal nobody activated for a while is out of date, so drop it
            cutoff = datetime.datetime.utcnow() - datetime.timedelta(minutes=PENDING_EXPIRE_MINUTES)
            stale = db.query(Trade).filter(Trade.market_type == market, Trade.status == "pending",
                                           Trade.created_at < cutoff).all()
            for t in stale:
                t.status = "expired"
            if stale:
                db.commit()

            open_trade = db.query(Trade).filter(
                Trade.market_type == market, Trade.status.in_(["pending", "active"])
            ).order_by(Trade.id.desc()).first()
            if open_trade:
                if open_trade.status == "pending":
                    engine.set_info(f"Signal #{open_trade.trade_number} {open_trade.asset} {open_trade.action} is waiting for ACTIVATE or SKIP")
                else:
                    engine.set_info(f"Waiting for you to log the result of trade #{open_trade.trade_number} ({open_trade.asset})")
                return

            rates = engine.get_forex_data(quality)
            counts = engine.scan_counts
            if not rates:
                if engine.quality_blocked(quality):
                    engine.set_info("High volatility: GOOD session blocked")
                elif counts["with_data"] == 0:
                    engine.set_info(f"No usable price data ({yf_data.summary()})")
                else:
                    engine.set_info(f"Scanned {counts['with_data']} pairs, none met {engine.get_min_conditions(quality)} conditions")
                return

            asset, direction, analysis, expiry = engine.get_confirmed_signal(rates, sessions, quality)
            if not asset:
                if not engine.groq_configured:
                    engine.set_info("Groq key missing, so setups cannot be confirmed")
                elif engine.groq_blocked_until and datetime.datetime.now() < engine.groq_blocked_until:
                    engine.set_info("Groq limit reached, retrying automatically")
                else:
                    engine.set_info(f"{len(rates)} setup(s) found, Groq did not give a HIGH confidence signal")
                return

            data = dict(rates[asset])
            data["expiry_mins"] = expiry
            data["groq"] = (analysis or "")[:500]
            last = db.query(Stats).order_by(Stats.id.desc()).first()
            tnum = last.trade_number if last and last.trade_number else 1
            level = three_min_martingale_level if market == "3min" else 0
            trade = Trade(
                trade_number=tnum, asset=asset, action=direction, expiry_mins=expiry,
                price=data["price"], confidence="High", status="pending", details=data,
                market_type=market, martingale_level=level, is_martingale=level > 0,
            )
            db.add(trade)
            db.commit()
            engine.set_info(f"Signal #{tnum} {asset} {direction} ready, waiting for ACTIVATE")
            print(f"[{engine.name}] SIGNAL {asset} {direction} {expiry}min")
            if personal_id:
                send_telegram(
                    f"{engine.name}: new signal ready\n{asset} {direction} ({expiry} min)\n"
                    f"Open the dashboard and tap ACTIVATE to post it.",
                    token, personal_id,
                )
        finally:
            db.close()
    except Exception as e:
        engine.set_info(f"Scan error: {e}")
        print(f"[SCANNER] {market}: {e}")
    finally:
        lock.release()

async def background_scanner():
    await asyncio.sleep(15)
    loop = asyncio.get_running_loop()
    while True:
        for market in ("patience", "3min"):
            auto_on = auto_scan_patience if market == "patience" else auto_scan_3min
            if auto_on:
                try:
                    await loop.run_in_executor(None, scan_market, market)
                except Exception as e:
                    print(f"[SCANNER] {market}: {e}")
        await asyncio.sleep(60)

@app.get("/status")
async def status():
    now = datetime.datetime.now()
    bots = {}
    for market, engine in ENGINES.items():
        blocked = bool(engine.groq_blocked_until and now < engine.groq_blocked_until)
        bots[market] = {
            "last_scan": engine.last_scan_info,
            "last_scan_at": engine.last_scan_at.isoformat() if engine.last_scan_at else None,
            "groq_configured": engine.groq_configured,
            "groq_limit_active": blocked,
            "high_volatility": getattr(engine, "high_volatility_mode", False),
            "cooldown_seconds": engine.cooldown_remaining(),
            "pairs_scanned": engine.scan_counts,
            "blacklisted": list(engine.blacklisted_pairs),
            "win_cooldown": list(engine.win_cooldown_pairs),
            "skipped": list(engine.skipped_pairs),
        }
    return JSONResponse({"price_data": yf_data.status(), "bots": bots})

@app.on_event("startup")
async def startup_event():
    for market, engine in ENGINES.items():
        token, chat_id, personal_id = get_token_and_chat(market)
        engine.notifier = lambda text, t=token, p=personal_id: send_telegram(text, t, p)
        engine.group_notifier = lambda text, t=token, c=chat_id: send_telegram(text, t, c)
    asyncio.create_task(background_scanner())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
