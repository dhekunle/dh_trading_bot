import os
from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import datetime
import pytz
from .database import init_db, get_db, Trade, Stats
from .signal_engine import SignalEngine

app = FastAPI(title="Forex Signal Bot")

# Create static folder if it doesn't exist (GitHub doesn't upload empty folders)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
# Disable cache to avoid Jinja2 "unhashable type: dict" bug on Render
templates.env.cache = None

init_db()
engine = SignalEngine()
WAT = pytz.timezone("Africa/Lagos")
bot_paused = False
scanning = False

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    sessions, quality, reason = engine.get_session_quality()
    stats = db.query(Stats).order_by(Stats.id.desc()).first()
    recent_trades = db.query(Trade).order_by(Trade.id.desc()).limit(15).all()
    
    # Convert to plain dicts so Jinja doesn't choke on JSON fields
    recent = []
    for t in recent_trades:
        recent.append({
            "id": t.id,
            "trade_number": t.trade_number,
            "asset": t.asset,
            "action": t.action,
            "expiry_mins": t.expiry_mins,
            "status": t.status or "pending",
            "result": t.result
        })
    
    stats_data = None
    if stats:
        stats_data = {
            "wins": stats.wins or 0,
            "losses": stats.losses or 0,
            "draws": stats.draws or 0,
            "trade_number": stats.trade_number or 1
        }
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "quality": quality,
        "reason": reason,
        "sessions": ", ".join(sessions) if sessions else "None",
        "stats": stats_data,
        "recent": recent,
        "paused": bot_paused,
        "scanning": scanning,
        "now": datetime.datetime.now(WAT).strftime("%Y-%m-%d %H:%M WAT")
    })

@app.post("/scan")
async def start_scan(db: Session = Depends(get_db)):
    global scanning
    if bot_paused:
        return RedirectResponse("/", status_code=303)
    scanning = True
    sessions, quality, reason = engine.get_session_quality()
    if quality in ["AVOID", "CLOSED"] or not sessions:
        scanning = False
        return RedirectResponse("/", status_code=303)
    
    rates = engine.get_forex_data(quality)
    if rates:
        # Take the strongest setup
        best = max(rates.items(), key=lambda x: x[1]["conditions"])
        asset, data = best
        # Create pending trade (appears on dashboard)
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
async def post_signal(trade_id: int, db: Session = Depends(get_db)):
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade or trade.status != "pending":
        return RedirectResponse("/", status_code=303)
    trade.status = "active"   # Now live on the dashboard
    db.commit()
    return RedirectResponse("/", status_code=303)

@app.post("/result/{trade_id}")
async def log_result(trade_id: int, result: str = Form(...), db: Session = Depends(get_db)):
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        return RedirectResponse("/", status_code=303)
    trade.result = result.upper()
    trade.status = result.lower()
    trade.resolved_at = datetime.datetime.utcnow()
    db.commit()
    
    # Update stats
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
async def toggle_pause():
    global bot_paused
    bot_paused = not bot_paused
    return RedirectResponse("/", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
