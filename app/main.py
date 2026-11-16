import hashlib
import os
import secrets
from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import datetime
import pytz
import asyncio
from .database import init_db, get_db, Trade, Stats, User
from .signal_engine import SignalEngine
from .config import SECRET_KEY

app = FastAPI(title="Forex Signal Bot")

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

init_db()
engine = SignalEngine()
WAT = pytz.timezone("Africa/Lagos")
bot_paused = False
scanning = False
auto_scan_enabled = True

def hash_password(password: str) -> str:
    # Simple salted hash (avoids bcrypt issues on Render)
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${hashed}"

def verify_password(plain: str, hashed: str) -> bool:
    try:
        salt, stored_hash = hashed.split("$", 1)
        return hashlib.sha256((salt + plain).encode()).hexdigest() == stored_hash
    except Exception:
        return False

def get_current_user(request: Request, db: Session):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return None
    user_id = sessions[session_id]
    return db.query(User).filter(User.id == user_id).first()

@app.get("/register", response_class=HTMLResponse)
async def register_page():
    return HTMLResponse('''
    <!DOCTYPE html>
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Create Account</title>
    <style>
        body { font-family: system-ui; background: #0f1117; color: #e4e6eb; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .box { background: #1a1d27; padding: 32px; border-radius: 12px; width: 340px; }
        input { width: 100%; padding: 10px; margin: 8px 0; border-radius: 6px; border: 1px solid #333; background: #0f1117; color: white; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #3b82f6; color: white; border: none; border-radius: 8px; font-weight: 600; margin-top: 8px; }
        a { color: #93c5fd; }
    </style></head>
    <body>
    <div class="box">
        <h2>Create Account</h2>
        <form method="post" action="/register">
            <input name="email" type="email" placeholder="Your Gmail" required>
            <input name="password" type="password" placeholder="Password" required minlength="6">
            <input name="confirm" type="password" placeholder="Confirm Password" required>
            <button type="submit">Create Account</button>
        </form>
        <p style="text-align:center; margin-top:16px;"><a href="/login">Already have an account? Login</a></p>
    </div>
    </body></html>
    ''')

@app.post("/register")
async def do_register(email: str = Form(...), password: str = Form(...), confirm: str = Form(...), db: Session = Depends(get_db)):
    if password != confirm:
        return RedirectResponse("/register?error=mismatch", status_code=303)
    if db.query(User).filter(User.email == email.lower()).first():
        return RedirectResponse("/register?error=exists", status_code=303)
    user = User(email=email.lower(), password_hash=hash_password(password))
    db.add(user)
    db.commit()
    return RedirectResponse("/login?registered=1", status_code=303)

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return HTMLResponse('''
    <!DOCTYPE html>
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Login</title>
    <style>
        body { font-family: system-ui; background: #0f1117; color: #e4e6eb; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .box { background: #1a1d27; padding: 32px; border-radius: 12px; width: 340px; }
        input { width: 100%; padding: 10px; margin: 8px 0; border-radius: 6px; border: 1px solid #333; background: #0f1117; color: white; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #3b82f6; color: white; border: none; border-radius: 8px; font-weight: 600; margin-top: 8px; }
        a { color: #93c5fd; }
    </style></head>
    <body>
    <div class="box">
        <h2>Login</h2>
        <form method="post" action="/login">
            <input name="email" type="email" placeholder="Your Gmail" required>
            <input name="password" type="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        <p style="text-align:center; margin-top:16px;"><a href="/register">Create an account</a></p>
    </div>
    </body></html>
    ''')

@app.post("/login")
async def do_login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user or not verify_password(password, user.password_hash):
        return RedirectResponse("/login?error=1", status_code=303)
    session_id = secrets.token_hex(16)
    sessions[session_id] = user.id
    response = RedirectResponse("/", status_code=303)
    response.set_cookie("session_id", session_id, httponly=True, max_age=60*60*24*7)
    return response

@app.get("/logout")
async def logout(request: Request):
    session_id = request.cookies.get("session_id")
    sessions.pop(session_id, None)
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("session_id")
    return response

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    
    sessions_list, quality, reason = engine.get_session_quality()
    stats = db.query(Stats).order_by(Stats.id.desc()).first()
    recent_trades = db.query(Trade).order_by(Trade.id.desc()).limit(15).all()
    
    stats_html = "<p>No stats yet</p>"
    if stats:
        stats_html = f"<p>Wins: {stats.wins or 0} · Losses: {stats.losses or 0} · Draws: {stats.draws or 0}</p><p>Next Trade #: {stats.trade_number or 1}</p>"
    
    rows = ""
    for t in recent_trades:
        status = t.status or "pending"
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
            <td>{t.trade_number}</td>
            <td>{t.asset}</td>
            <td>{t.action}</td>
            <td>{t.expiry_mins}m</td>
            <td class="{status}">{status.upper()}</td>
            <td>{actions}</td>
        </tr>
        '''
    
    pause_label = "Resume" if bot_paused else "Pause"
    bot_status = "PAUSED" if bot_paused else "ACTIVE"
    auto_status = "ON" if auto_scan_enabled else "OFF"
    now = datetime.datetime.now(WAT).strftime("%Y-%m-%d %H:%M WAT")
    sessions_str = ", ".join(sessions_list) if sessions_list else "None"
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Forex Signal Bot</title>
    <style>
        :root {{ --bg: #0f1117; --card: #1a1d27; --text: #e4e6eb; --accent: #3b82f6; --green: #22c55e; --red: #ef4444; }}
        body {{ font-family: system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        h1 {{ margin-bottom: 8px; }}
        .card {{ background: var(--card); border-radius: 12px; padding: 20px; margin-bottom: 16px; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
        .btn {{ background: var(--accent); color: white; border: none; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-weight: 600; }}
        .btn:hover {{ opacity: 0.9; }}
        .btn-green {{ background: var(--green); }}
        .btn-red {{ background: var(--red); }}
        .btn-gray {{ background: #4b5563; }}
        .status {{ font-size: 0.9em; color: #9ca3af; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #2d313c; }}
        .pending {{ color: #fbbf24; }}
        .win {{ color: var(--green); }}
        .loss {{ color: var(--red); }}
        a {{ color: #93c5fd; }}
    </style>
</head>
<body>
<div class="container">
    <h1>Forex Signal Bot <small style="font-size:0.5em;">{user.email} · <a href="/logout">Logout</a></small></h1>
    <p class="status">{now} · Session: {sessions_str} · Quality: <strong>{quality}</strong> ({reason}) · Auto-scan: {auto_status}</p>
    
    <div class="grid">
        <div class="card">
            <h3>Controls</h3>
            <form action="/scan" method="post" style="display:inline;">
                <button class="btn" {"disabled" if bot_paused else ""}>Scan Now</button>
            </form>
            <form action="/pause" method="post" style="display:inline; margin-left:8px;">
                <button class="btn btn-gray">{pause_label}</button>
            </form>
            <form action="/toggle-auto" method="post" style="display:inline; margin-left:8px;">
                <button class="btn btn-gray">Auto-scan: {auto_status}</button>
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
</div>
</body>
</html>'''
    
    return HTMLResponse(content=html)

@app.post("/scan")
async def start_scan(request: Request, db: Session = Depends(get_db)):
    if not get_current_user(request, db):
        return RedirectResponse("/login", status_code=303)
    global scanning
    if bot_paused:
        return RedirectResponse("/", status_code=303)
    scanning = True
    sessions_list, quality, reason = engine.get_session_quality()
    if quality in ["AVOID", "CLOSED"] or not sessions_list:
        scanning = False
        return RedirectResponse("/", status_code=303)
    
    rates = engine.get_forex_data(quality)
    if rates:
        best = max(rates.items(), key=lambda x: x[1]["conditions"])
        asset, data = best
        last = db.query(Stats).order_by(Stats.id.desc()).first()
        tnum = (last.trade_number if last else 1)
        trade = Trade(
            trade_number=tnum,
            asset=asset,
            action=data["signal"],
            expiry_mins=data["expiry_mins"],
            price=data["price"],
            status="pending",
            details=data
        )
        db.add(trade)
        db.commit()
    scanning = False
    return RedirectResponse("/", status_code=303)

@app.post("/post/{trade_id}")
async def post_signal(trade_id: int, request: Request, db: Session = Depends(get_db)):
    if not get_current_user(request, db):
        return RedirectResponse("/login", status_code=303)
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade or trade.status != "pending":
        return RedirectResponse("/", status_code=303)
    trade.status = "active"
    db.commit()
    return RedirectResponse("/", status_code=303)

@app.post("/result/{trade_id}")
async def log_result(trade_id: int, request: Request, result: str = Form(...), db: Session = Depends(get_db)):
    if not get_current_user(request, db):
        return RedirectResponse("/login", status_code=303)
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
    return RedirectResponse("/", status_code=303)

@app.post("/pause")
async def toggle_pause(request: Request, db: Session = Depends(get_db)):
    if not get_current_user(request, db):
        return RedirectResponse("/login", status_code=303)
    global bot_paused
    bot_paused = not bot_paused
    return RedirectResponse("/", status_code=303)

@app.post("/toggle-auto")
async def toggle_auto(request: Request, db: Session = Depends(get_db)):
    if not get_current_user(request, db):
        return RedirectResponse("/login", status_code=303)
    global auto_scan_enabled
    auto_scan_enabled = not auto_scan_enabled
    return RedirectResponse("/", status_code=303)

async def background_scanner():
    await asyncio.sleep(10)
    while True:
        try:
            if auto_scan_enabled and not bot_paused and not scanning:
                sessions_list, quality, reason = engine.get_session_quality()
                if quality not in ["AVOID", "CLOSED"] and sessions_list:
                    from .database import SessionLocal
                    db = SessionLocal()
                    try:
                        rates = engine.get_forex_data(quality)
                        if rates:
                            best = max(rates.items(), key=lambda x: x[1]["conditions"])
                            asset, data = best
                            if data.get("conditions", 0) >= 3:
                                last = db.query(Stats).order_by(Stats.id.desc()).first()
                                tnum = (last.trade_number if last else 1)
                                recent = db.query(Trade).filter(Trade.asset == asset).order_by(Trade.id.desc()).first()
                                if not recent or (datetime.datetime.utcnow() - (recent.created_at or datetime.datetime.utcnow())).total_seconds() > 900:
                                    trade = Trade(
                                        trade_number=tnum,
                                        asset=asset,
                                        action=data["signal"],
                                        expiry_mins=data["expiry_mins"],
                                        price=data["price"],
                                        status="pending",
                                        details=data
                                    )
                                    db.add(trade)
                                    db.commit()
                                    print(f"[AUTO] New signal: {asset} {data['signal']}")
                    finally:
                        db.close()
        except Exception as e:
            print(f"[AUTO] Scanner error: {e}")
        await asyncio.sleep(180)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_scanner())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
