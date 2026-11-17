import os
from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import datetime
import pytz
import asyncio
from .database import init_db, get_db, Trade, Stats
from .signal_engine import SignalEngine
from .signal_engine_3min import SignalEngine3Min
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
    mg = f" (Martingale {trade.martingale_level})" if trade.martingale_level else ""
    bot_name = "Patience Bot" if trade.market_type == "patience" else "3 min Bot"
    now_wat = datetime.datetime.now(WAT).strftime("%Y-%m-%d %H:%M WAT")
    return (
        f"<b>{bot_name} Signal</b>{mg}\n"
        f"{now_wat}\n\n"
        f"Trade #{trade.trade_number}\n"
        f"Asset: {trade.asset}\n"
        f"Action: {trade.action}\n"
        f"Expiry: {trade.expiry_mins} min\n"
        f"Price: {trade.price}"
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
            actions += f'<form action="/post/{t.id}" method="post" style="display:inline;"><button class="btn btn-green" style="padding:6px 12px;font-size:0.85em;">ACTIVATE</button></form> '
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
    if market == "3min" and hasattr(engine, "high_volatility_mode") and engine.high_volatility_mode:
        vol_tag = " · STRICT MODE (High Volatility)"
    
    html = f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title>{STYLE}</head>
<body><div class="container">
    <h1>{title} {back}</h1>
    <p class="status">{now}{q_info}{vol_tag} · Auto-scan: {auto_status}</p>
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
    html = build_dashboard("patience", db, bot_paused_patience, auto_scan_patience, (sessions, quality, reason))
    return HTMLResponse(html)

@app.get("/3min", response_class=HTMLResponse)
async def three_min_dashboard(db: Session = Depends(get_db)):
    sessions, quality, reason = three_min_engine.get_session_quality()
    html = build_dashboard("3min", db, bot_paused_3min, auto_scan_3min, (sessions, quality, reason), three_min_engine)
    return HTMLResponse(html)

@app.post("/scan/{market}")
async def start_scan(market: str, db: Session = Depends(get_db)):
    global scanning_patience, scanning_3min
    if market == "patience":
        if bot_paused_patience:
            return RedirectResponse("/patience", status_code=303)
        scanning_patience = True
        sessions, quality, reason = patience_engine.get_session_quality()
        if quality in ["AVOID", "CLOSED"] or not sessions:
            scanning_patience = False
            return RedirectResponse("/patience", status_code=303)
        rates = patience_engine.get_forex_data(quality)
        if rates:
            best = max(rates.items(), key=lambda x: x[1]["conditions"])
            asset, data = best
            last = db.query(Stats).order_by(Stats.id.desc()).first()
            tnum = (last.trade_number if last else 1)
            trade = Trade(
                trade_number=tnum, asset=asset, action=data["signal"],
                expiry_mins=data["expiry_mins"], price=data["price"],
                status="pending", details=data, market_type="patience", martingale_level=0
            )
            db.add(trade)
            db.commit()
        scanning_patience = False
        return RedirectResponse("/patience", status_code=303)
    else:
        if bot_paused_3min:
            return RedirectResponse("/3min", status_code=303)
        scanning_3min = True
        three_min_engine.check_volatility()
        sessions, quality, reason = three_min_engine.get_session_quality()
        rates = three_min_engine.get_forex_data(quality or "GOOD")
        if rates:
            best = max(rates.items(), key=lambda x: x[1]["conditions"])
            asset, data = best
            last = db.query(Stats).order_by(Stats.id.desc()).first()
            tnum = (last.trade_number if last else 1)
            global three_min_martingale_level
            trade = Trade(
                trade_number=tnum, asset=asset, action=data["signal"],
                expiry_mins=data["expiry_mins"], price=data["price"],
                status="pending", details=data, market_type="3min",
                martingale_level=three_min_martingale_level, is_martingale=three_min_martingale_level > 0
            )
            db.add(trade)
            db.commit()
        scanning_3min = False
        return RedirectResponse("/3min", status_code=303)

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
    if not trade:
        return RedirectResponse("/", status_code=303)
    trade.result = result.upper()
    trade.status = result.lower()
    trade.resolved_at = datetime.datetime.utcnow()
    db.commit()
    
    stats = db.query(Stats).order_by(Stats.id.desc()).first()
    if not stats:
        stats = Stats(week=datetime.datetime.now(WAT).strftime("%Y-W%W"))
        db.add(stats)
    if result.upper() == "WIN":
        stats.wins += 1
    elif result.upper() == "LOSS":
        stats.losses += 1
    elif result.upper() == "DRAW":
        stats.draws += 1
    stats.total += 1
    stats.trade_number = trade.trade_number + 1
    db.commit()
    # Post result to the correct Telegram group
    result_msg = f"Trade #{trade.trade_number} - {result.upper()}!\n{trade.asset} {trade.action}"
    token, chat_id, personal_id = get_token_and_chat(trade.market_type)
    send_telegram(result_msg, token, chat_id)
    if personal_id:
        send_telegram(result_msg, token, personal_id)
    
    if trade.market_type == "3min":
        global last_3min_result_time, three_min_martingale_level
        last_3min_result_time = datetime.datetime.utcnow()
        if result.upper() == "LOSS":
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

async def background_scanner():
    global last_3min_result_time, three_min_martingale_level
    await asyncio.sleep(15)
    while True:
        try:
            # Patience Bot auto scan
            if auto_scan_patience and not bot_paused_patience and not scanning_patience:
                sessions, quality, reason = patience_engine.get_session_quality()
                if quality not in ["AVOID", "CLOSED"] and sessions:
                    from .database import SessionLocal
                    db = SessionLocal()
                    try:
                        rates = patience_engine.get_forex_data(quality)
                        if rates:
                            best = max(rates.items(), key=lambda x: x[1]["conditions"])
                            asset, data = best
                            if data.get("conditions", 0) >= 3:
                                last = db.query(Stats).order_by(Stats.id.desc()).first()
                                tnum = (last.trade_number if last else 1)
                                recent = db.query(Trade).filter(Trade.asset == asset, Trade.market_type == "patience").order_by(Trade.id.desc()).first()
                                if not recent or (datetime.datetime.utcnow() - (recent.created_at or datetime.datetime.utcnow())).total_seconds() > 900:
                                    trade = Trade(
                                        trade_number=tnum, asset=asset, action=data["signal"],
                                        expiry_mins=data["expiry_mins"], price=data["price"],
                                        status="pending", details=data, market_type="patience", martingale_level=0
                                    )
                                    db.add(trade)
                                    db.commit()
                                    print(f"[PATIENCE AUTO] {asset} {data['signal']}")
                    finally:
                        db.close()
            
            # 3 min Bot: only after 3 minutes from last result
            if auto_scan_3min and not bot_paused_3min and not scanning_3min:
                now = datetime.datetime.utcnow()
                can_send = False
                if last_3min_result_time is None:
                    can_send = True
                elif (now - last_3min_result_time).total_seconds() >= 180:
                    can_send = True
                if can_send:
                    three_min_engine.check_volatility()
                    sessions, quality, reason = three_min_engine.get_session_quality()
                    if quality not in ["AVOID", "CLOSED"]:
                        from .database import SessionLocal
                        db = SessionLocal()
                        try:
                            rates = three_min_engine.get_forex_data(quality or "GOOD")
                            if rates:
                                best = max(rates.items(), key=lambda x: x[1]["conditions"])
                                asset, data = best
                                last = db.query(Stats).order_by(Stats.id.desc()).first()
                                tnum = (last.trade_number if last else 1)
                                trade = Trade(
                                    trade_number=tnum, asset=asset, action=data["signal"],
                                    expiry_mins=data["expiry_mins"], price=data["price"],
                                    status="pending", details=data, market_type="3min",
                                    martingale_level=three_min_martingale_level,
                                    is_martingale=three_min_martingale_level > 0
                                )
                                db.add(trade)
                                db.commit()
                                print(f"[3MIN AUTO] MG{three_min_martingale_level} {asset} {data['signal']}")
                                last_3min_result_time = now
                        finally:
                            db.close()
        except Exception as e:
            print(f"[SCANNER] {e}")
        await asyncio.sleep(30)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_scanner())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
