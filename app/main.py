import os
from pathlib import Path
import html as htmllib
import threading
import secrets
from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
import datetime
import pytz
import asyncio
from .database import init_db, get_db, SessionLocal, Trade, Stats, User, ChatMessage
from .signal_engine import SignalEngine
from .signal_engine_3min import SignalEngine3Min
from .engine_core import news_status, SKIP_BAN_MINUTES
from . import yf_data, auth, ui
import requests
from .config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_TOKEN_3MIN,
    TELEGRAM_CHAT_ID, TELEGRAM_CHAT_ID_3MIN,
    MY_PERSONAL_CHAT_ID, MY_PERSONAL_CHAT_ID_3MIN,
    ADMIN_USERNAME, ADMIN_PASSWORD, SECRET_KEY, REQUIRE_APPROVAL
)

app = FastAPI(title="DH Binary Trader")

# ---- access control -------------------------------------------------------
ADMIN_PREFIXES = ("/admin", "/scan/", "/post/", "/result/", "/skip/", "/pause/", "/toggle-auto/", "/status")
USER_PREFIXES = ("/app", "/api/")

@app.middleware("http")
async def access_guard(request: Request, call_next):
    path = request.url.path
    if path.startswith(ADMIN_PREFIXES) and not path.startswith("/admin/login"):
        if not request.session.get("admin"):
            return RedirectResponse("/admin/login", status_code=303)
    elif path.startswith(USER_PREFIXES):
        if not (request.session.get("uid") or request.session.get("admin")):
            if path.startswith("/api/"):
                return JSONResponse({"error": "login required"}, status_code=401)
            return RedirectResponse("/login", status_code=303)
    return await call_next(request)

# Added after the guard so sessions are available to it
_default_secrets = {"", "change-me-in-production", "change_this_to_a_random_secret", "your_secret_key_here"}
if SECRET_KEY in _default_secrets:
    print("[WARN] SECRET_KEY is not set. Using a temporary key, so everyone is logged out on every restart.")
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY if SECRET_KEY not in _default_secrets else secrets.token_hex(32),
    session_cookie="dh_session",
    max_age=60 * 60 * 24 * 30,
    same_site="lax",
    https_only=bool(os.getenv("RENDER")),
)

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

def admin_path(market: str) -> str:
    return "/admin/3min" if market == "3min" else "/admin/patience"

def get_token_and_chat(market_type: str):
    """Returns (bot token, group chat id, personal chat id) for a bot.

    The 3 min Bot may have its own Telegram bot and group. A token and a group are never
    mixed between the two bots: if the 3 min token is set, the 3 min group must be set too.
    """
    if market_type == "3min":
        if TELEGRAM_BOT_TOKEN_3MIN or TELEGRAM_CHAT_ID_3MIN:
            return (TELEGRAM_BOT_TOKEN_3MIN or TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID_3MIN,
                    MY_PERSONAL_CHAT_ID_3MIN or MY_PERSONAL_CHAT_ID)
    return TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, MY_PERSONAL_CHAT_ID

telegram_status = {"patience": "Telegram: nothing posted yet", "3min": "Telegram: nothing posted yet"}

TELEGRAM_HINTS = (
    ("chat not found", "chat ID is wrong, or the bot was never added to that group"),
    ("bot was kicked", "the bot was removed from the group, add it back as admin"),
    ("not a member", "add the bot to the group as admin"),
    ("not enough rights", "make the bot an admin that can post messages"),
    ("have no rights", "make the bot an admin that can post messages"),
    ("unauthorized", "the bot token is wrong"),
    ("blocked by the user", "open the bot in Telegram and press Start"),
)

def send_telegram(text: str, token: str, chat_id: str, market: str = None) -> bool:
    """Send a message. Pass market only for group posts so the dashboard can show the outcome."""
    def note(message):
        if market:
            telegram_status[market] = message
    stamp = datetime.datetime.now(WAT).strftime("%I:%M %p")
    if not token:
        note("Telegram FAILED: bot token is missing")
        return False
    if not chat_id:
        note("Telegram FAILED: group chat ID is missing" + (" (TELEGRAM_CHAT_ID_3MIN)" if market == "3min" else ""))
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
        try:
            data = r.json()
        except Exception:
            data = {}
        if r.status_code == 200 and data.get("ok"):
            note(f"Telegram OK (last post {stamp})")
            return True
        reason = str(data.get("description") or f"HTTP {r.status_code}")
        hint = next((h for key, h in TELEGRAM_HINTS if key in reason.lower()), "")
        note(f"Telegram FAILED: {reason}" + (f" - {hint}" if hint else ""))
        print(f"[TELEGRAM] {market or 'private'} failed: {reason}")
        return False
    except Exception as e:
        reason = str(e).replace(token, "***")[:150]
        note(f"Telegram FAILED: {reason}")
        print(f"[TELEGRAM] {market or 'private'} error: {reason}")
        return False

STICKER_DIR = Path(__file__).resolve().parent / "assets" / "stickers"

def send_telegram_photo(filename: str, token: str, chat_id: str, market: str = None) -> bool:
    """Send one of the bundled session pictures to a Telegram group."""
    def note(message):
        if market:
            telegram_status[market] = message
    path = STICKER_DIR / filename
    if not token or not chat_id:
        note("Telegram FAILED: bot token or group chat ID is missing")
        return False
    if not path.exists():
        note(f"Telegram FAILED: picture {filename} is missing from the app")
        return False
    try:
        with open(path, "rb") as f:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data={"chat_id": chat_id}, files={"photo": (filename, f, "image/jpeg")}, timeout=20,
            )
        try:
            data = r.json()
        except Exception:
            data = {}
        if r.status_code == 200 and data.get("ok"):
            note(f"Telegram OK (last post {datetime.datetime.now(WAT).strftime('%I:%M %p')})")
            return True
        reason = str(data.get("description") or f"HTTP {r.status_code}")
        hint = next((h for key, h in TELEGRAM_HINTS if key in reason.lower()), "")
        note(f"Telegram FAILED: {reason}" + (f" - {hint}" if hint else ""))
        return False
    except Exception as e:
        reason = str(e).replace(token, "***")[:150]
        note(f"Telegram FAILED: {reason}")
        return False

def build_signal_message(trade: Trade, now=None) -> str:
    """Group message in the same format as the original bots."""
    engine = ENGINES.get(trade.market_type, patience_engine)
    sessions, quality, _ = engine.get_session_quality()
    session_text = ", ".join(sessions) if sessions else "No active session"
    vol_tag = "\nSTRICT MODE - High Volatility" if getattr(engine, "high_volatility_mode", False) else ""
    now = now or datetime.datetime.now(WAT)
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
:root{color-scheme:dark;--bg:#090a0f;--line:#292d3b;--text:#eef0f6;--muted:#9299aa;--purple:#9b7bff;--green:#27cf83;--red:#ff5368;--amber:#f3bd4f}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 82% -10%,#211a3b 0,transparent 35%),var(--bg);color:var(--text);font:15px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,sans-serif;padding:24px}.container{max-width:1180px;margin:0 auto}.top{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:22px}.brand{display:flex;align-items:center;gap:14px}.mark{width:48px;height:48px;border:1px solid #4b3c78;border-radius:15px;display:grid;place-items:center;color:var(--purple);font-size:24px;background:#171322}.brand h1{font-size:25px;line-height:1.1;margin:0}.brand p{margin:5px 0 0;color:var(--muted);font-size:13px}.adminlink{color:#c7b9ff;text-decoration:none;border:1px solid var(--line);background:#151722;padding:10px 14px;border-radius:12px}.statusbar{display:grid;grid-template-columns:1.1fr 1.3fr .8fr;background:linear-gradient(120deg,#151622,#10121a);border:1px solid var(--line);border-radius:18px;padding:17px 18px;margin-bottom:14px}.statusitem{padding:0 18px;border-right:1px solid var(--line)}.statusitem:first-child{padding-left:0}.statusitem:last-child{border:0}.eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);font-weight:700}.value{font-size:17px;font-weight:700;margin-top:4px}.muted{color:var(--muted)}.green{color:var(--green)}.red{color:var(--red)}.purple{color:var(--purple)}.amber{color:var(--amber)}.notice{background:#121827;border:1px solid #293b60;color:#b9c8e9;border-radius:14px;padding:13px 16px;margin-bottom:18px;font-size:13px}.notice strong{color:#e6ebff}.layout{display:grid;grid-template-columns:1.05fr .95fr;gap:16px;margin-bottom:16px}.panel{background:linear-gradient(145deg,rgba(24,26,38,.98),rgba(14,16,23,.98));border:1px solid var(--line);border-radius:20px;padding:20px;box-shadow:0 12px 36px #0003}.panelhead{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:17px}.panelhead h2{font-size:17px;margin:0}.chip{border:1px solid #383149;color:#c8baff;background:#1b1728;padding:5px 9px;border-radius:99px;font-size:11px;font-weight:700}.controls{display:grid;grid-template-columns:1fr 1fr;gap:10px}.btn{display:flex;align-items:center;justify-content:center;gap:9px;min-height:48px;padding:12px 14px;border:1px solid var(--line);border-radius:13px;background:#202331;color:var(--text);font-weight:700;font-size:13px;text-decoration:none;cursor:pointer}.btn:hover{filter:brightness(1.12)}.btn-primary{background:linear-gradient(110deg,#7654d6,#4c3a8d);border-color:#8066ce}.btn-green{background:#123528;border-color:#236c4d;color:#7ce4b1}.btn-danger{background:#351b25;border-color:#713344;color:#ff9aaa}.btn:disabled{opacity:.4}.botstate{display:flex;align-items:center;gap:9px;color:var(--muted);font-size:13px;margin-top:15px}.dot{width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:0 0 12px #27cf8377}.statsgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.stat{background:#0e1018;border:1px solid #242838;border-radius:14px;padding:13px 12px;min-width:0}.stat .num{font-size:25px;font-weight:750;letter-spacing:-.04em;margin-top:4px}.stat .label{font-size:11px;color:var(--muted)}.ratebar{height:5px;border-radius:5px;background:#282b39;margin-top:9px;overflow:hidden}.ratebar span{display:block;height:100%;background:var(--purple);border-radius:5px}.tablewrap{overflow-x:auto}.signals{width:100%;border-collapse:collapse;min-width:620px}.signals th{text-align:left;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.09em;padding:11px 10px;border-bottom:1px solid var(--line)}.signals td{padding:13px 10px;border-bottom:1px solid #222633;font-size:13px}.signals tr:last-child td{border-bottom:0}.asset{font-weight:750;letter-spacing:.02em}.tag{display:inline-flex;align-items:center;gap:6px;padding:5px 9px;border-radius:8px;font-size:11px;font-weight:800;background:#202332;color:#cbd0df}.tag.buy,.tag.win{background:#123528;color:#70e1aa}.tag.sell,.tag.loss{background:#381d28;color:#ff9aaa}.tag.pending{background:#352b19;color:#f4ca70}.tag.skipped,.tag.expired,.tag.draw{background:#242735;color:#adb4c8}.rowactions{display:flex;gap:6px;align-items:center}.mini{padding:6px 9px;min-height:30px;font-size:11px;border-radius:8px}.footerline{color:var(--muted);font-size:11px;margin:15px 2px 0;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}.empty{text-align:center;color:var(--muted);padding:28px!important}
@media(max-width:760px){body{padding:15px}.brand h1{font-size:21px}.statusbar{grid-template-columns:1fr 1fr;row-gap:14px}.statusitem{padding:0 10px}.statusitem:nth-child(2){border:0}.statusitem:last-child{grid-column:1/-1;padding-left:0;border-top:1px solid var(--line);padding-top:12px}.layout{grid-template-columns:1fr}.statsgrid{grid-template-columns:repeat(2,1fr)}.panel{padding:16px}.controls{gap:8px}.btn{font-size:12px;padding:10px 8px}}
@media(max-width:390px){.statusbar{grid-template-columns:1fr}.statusitem,.statusitem:nth-child(2){padding:0;border:0}.statusitem:last-child{grid-column:auto}.controls{grid-template-columns:1fr 1fr}}
</style>
'''

@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    return {"status": "ok"}

def build_dashboard(market: str, db: Session, paused: bool, auto_on: bool, quality_info=None, engine=None):
    trades = db.query(Trade).filter(Trade.market_type == market).order_by(Trade.id.desc()).limit(20).all()
    stats = db.query(Stats).order_by(Stats.id.desc()).first()
    wins = int((stats.wins or 0) if stats else 0)
    losses = int((stats.losses or 0) if stats else 0)
    draws = int((stats.draws or 0) if stats else 0)
    total = wins + losses + draws
    decided = wins + losses
    win_rate = round(wins * 100 / decided) if decided else 0
    next_trade = int((stats.trade_number or 1) if stats else 1)
    title = "Patience Bot" if market == "patience" else "3 min Bot"
    now = datetime.datetime.now(WAT).strftime("%a, %d %b %Y · %H:%M WAT")
    sessions, quality, reason = quality_info or ([], "UNKNOWN", "Session status unavailable")
    session_text = ", ".join(sessions) if sessions else "No active session"
    q_class = "amber" if quality == "AVOID" else ("green" if quality not in ("CLOSED", "UNKNOWN") else "muted")
    auto_status = "ON" if auto_on else "OFF"
    bot_status = "PAUSED" if paused else "ACTIVE"
    scan_line = "Waiting for first scan"
    if engine is not None:
        when = engine.last_scan_at.strftime("%H:%M:%S") if engine.last_scan_at else "never"
        groq_state = "Groq connected" if engine.groq_configured else "Groq key missing"
        scan_line = f"Last scan {when}: {engine.last_scan_info} · {yf_data.summary()} · {groq_state} · {telegram_status.get(market, '')}"
    scan_line = htmllib.escape(scan_line)
    vol_text = " · Strict volatility mode" if engine is not None and getattr(engine, "high_volatility_mode", False) else ""
    rows = []
    for t in trades:
        status = (t.status or "pending").lower()
        result = (t.result or "").lower()
        action_class = "buy" if (t.action or "").upper() == "BUY" else "sell"
        status_class = result if result in ("win", "loss", "draw") else status
        mg = f" · MG{int(t.martingale_level)}" if t.martingale_level else ""
        actions = []
        if status == "active" and not t.result:
            actions.append(f'<form action="/skip/{t.id}" method="post"><button class="btn btn-danger mini" type="submit">Skip</button></form>')
            actions.append(f'<form action="/result/{t.id}" method="post"><input type="hidden" name="result" value="WIN"><button class="btn btn-green mini" type="submit">Win</button></form>')
            actions.append(f'<form action="/result/{t.id}" method="post"><input type="hidden" name="result" value="LOSS"><button class="btn btn-danger mini" type="submit">Loss</button></form>')
            actions.append(f'<form action="/result/{t.id}" method="post"><input type="hidden" name="result" value="DRAW"><button class="btn mini" type="submit">Draw</button></form>')
        elif status == "pending":
            actions.append(f'<form action="/post/{t.id}" method="post"><button class="btn btn-primary mini" type="submit">Post</button></form>')
            actions.append(f'<form action="/skip/{t.id}" method="post"><button class="btn btn-danger mini" type="submit">Skip</button></form>')
        asset = htmllib.escape(str(t.asset or "—"))
        action = htmllib.escape(str(t.action or "—").upper())
        rows.append(f'<tr><td>#{int(t.trade_number or 0)}{mg}</td><td class="asset">{asset}</td><td><span class="tag {action_class}">{action}</span></td><td>{int(t.expiry_mins or 0)}m</td><td><span class="tag {status_class}">{htmllib.escape((t.result or status).upper())}</span></td><td><div class="rowactions">{"".join(actions) or "<span class=muted>—</span>"}</div></td></tr>')
    rows_html = "".join(rows) if rows else '<tr><td colspan="6" class="empty">No signals recorded yet</td></tr>'
    pause_label = "Resume bot" if paused else "Pause bot"
    pause_class = "btn-green" if paused else ""
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#090a0f"><meta http-equiv="refresh" content="20"><title>{title} · Admin</title>{STYLE}</head>
<body><main class="container">
<header class="top"><div class="brand"><div class="mark">⌁</div><div><h1>{title}</h1><p>DH Binary Trader <span class="muted">/ Operations console</span></p></div></div><a class="adminlink" href="/admin">← Admin hub</a></header>
<section class="statusbar"><div class="statusitem"><div class="eyebrow">Market session</div><div class="value">{htmllib.escape(session_text)}</div><div class="muted" style="font-size:12px">{now}</div></div><div class="statusitem"><div class="eyebrow">Market quality</div><div class="value {q_class}">{htmllib.escape(str(quality))}</div><div class="muted" style="font-size:12px">{htmllib.escape(str(reason))}{htmllib.escape(vol_text)}</div></div><div class="statusitem"><div class="eyebrow">Auto scan · Bot</div><div class="value {'green' if auto_on and not paused else 'amber'}">{auto_status} · {bot_status}</div><div class="muted" style="font-size:12px">Next trade #{next_trade}</div></div></section>
<div class="notice"><strong>System status</strong> · {scan_line}</div>
<section class="layout"><article class="panel"><div class="panelhead"><h2>Bot controls</h2><span class="chip">{bot_status}</span></div><div class="controls">
<form action="/scan/{market}" method="post"><button class="btn btn-primary" type="submit" {'disabled' if paused else ''}>↻ &nbsp; Scan now</button></form>
<form action="/admin/telegram-test/{market}" method="post"><button class="btn" type="submit">➤ &nbsp; Test Telegram</button></form>
<form action="/pause/{market}" method="post"><button class="btn {pause_class}" type="submit">Ⅱ &nbsp; {pause_label}</button></form>
<form action="/toggle-auto/{market}" method="post"><button class="btn" type="submit">Auto-scan: <span class="{'green' if auto_on else 'amber'}">{auto_status}</span></button></form>
</div><div class="botstate"><span class="dot" style="background:{'var(--amber)' if paused else 'var(--green)'}"></span>{'Bot is paused. Automatic scanning is suspended.' if paused else 'Bot is running. Qualified signals publish automatically to Telegram.'}</div></article>
<article class="panel"><div class="panelhead"><h2>Performance summary</h2><span class="chip">All recorded results</span></div><div class="statsgrid">
<div class="stat"><div class="label">WINS</div><div class="num green">{wins}</div></div><div class="stat"><div class="label">LOSSES</div><div class="num red">{losses}</div></div><div class="stat"><div class="label">DRAWS</div><div class="num">{draws}</div></div><div class="stat"><div class="label">WIN RATE</div><div class="num purple">{win_rate}%</div><div class="ratebar"><span style="width:{win_rate}%"></span></div></div>
</div><div class="footerline"><span>{total} results recorded</span><span>Next trade #{next_trade}</span></div></article></section>
<section class="panel"><div class="panelhead"><h2>Recent signals</h2><span class="chip">Latest {len(trades)} records</span></div><div class="tablewrap"><table class="signals"><thead><tr><th>Trade</th><th>Asset</th><th>Direction</th><th>Expiry</th><th>Status</th><th>Actions</th></tr></thead><tbody>{rows_html}</tbody></table></div><div class="footerline"><span>Signals are published automatically after passing all bot filters.</span><span>Skip is available here after publication.</span></div></section>
<footer class="footerline"><span>DH Binary Trader · {title}</span><span>{htmllib.escape(telegram_status.get(market, 'Telegram status unavailable'))}</span></footer>
</main></body></html>'''
    return html


@app.get("/admin/patience", response_class=HTMLResponse)
async def patience_dashboard(db: Session = Depends(get_db)):
    sessions, quality, reason = patience_engine.get_session_quality()
    html = build_dashboard("patience", db, bot_paused_patience, auto_scan_patience, (sessions, quality, reason), patience_engine)
    return HTMLResponse(html)

@app.get("/admin/3min", response_class=HTMLResponse)
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
    return RedirectResponse(admin_path(m), status_code=303)

@app.post("/skip/{trade_id}")
async def skip_signal(trade_id: int, db: Session = Depends(get_db)):
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade or trade.status not in ("pending", "active") or trade.result:
        return RedirectResponse("/admin", status_code=303)
    trade.status = "skipped"
    db.commit()
    engine = ENGINES.get(trade.market_type, patience_engine)
    engine.skip_pair(trade.asset)
    engine.set_info(f"{trade.asset} skipped and banned for {SKIP_BAN_MINUTES} min. Scanning again.")
    return RedirectResponse(admin_path(trade.market_type), status_code=303)

@app.post("/post/{trade_id}")
async def post_signal(trade_id: int, db: Session = Depends(get_db)):
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade or trade.status != "pending":
        return RedirectResponse("/admin", status_code=303)
    now = datetime.datetime.now(WAT)
    entry = now + datetime.timedelta(minutes=1)
    expire = entry + datetime.timedelta(minutes=trade.expiry_mins)
    mart_entry = expire + datetime.timedelta(minutes=1)
    mart_expire = mart_entry + datetime.timedelta(minutes=trade.expiry_mins)
    details = dict(trade.details or {})
    details.update({k: v.astimezone(datetime.timezone.utc).isoformat() for k, v in {
        "activated_at": now, "entry_at": entry, "expire_at": expire,
        "mart_entry_at": mart_entry, "mart_expire_at": mart_expire}.items()})
    trade.details = details
    trade.status = "active"
    db.commit()
    # Post to the correct Telegram group using the correct token
    token, chat_id, personal_id = get_token_and_chat(trade.market_type)
    send_telegram(build_signal_message(trade, now), token, chat_id, market=trade.market_type)
    if personal_id:
        send_telegram(f"Activated: {trade.asset} {trade.action}", token, personal_id)
    redir = admin_path(trade.market_type)
    return RedirectResponse(redir, status_code=303)

@app.post("/result/{trade_id}")
async def log_result(trade_id: int, result: str = Form(...), db: Session = Depends(get_db)):
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    result = (result or "").upper()
    if not trade or trade.result or result not in ("WIN", "LOSS", "DRAW"):
        return RedirectResponse("/admin", status_code=303)
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
    send_telegram(result_msg, token, chat_id, market=trade.market_type)
    if personal_id:
        send_telegram(result_msg, token, personal_id)

    # Protections: win cooldown, loss blacklist, pause after consecutive losses
    engine = ENGINES.get(trade.market_type, patience_engine)
    cooldown_msg = engine.register_result(trade.asset, result)
    if cooldown_msg:
        send_telegram(cooldown_msg, token, chat_id, market=trade.market_type)
        if personal_id:
            send_telegram(cooldown_msg, token, personal_id)

    if trade.market_type == "3min":
        global last_3min_result_time, three_min_martingale_level
        last_3min_result_time = datetime.datetime.utcnow()
        if result == "LOSS":
            three_min_martingale_level = min(three_min_martingale_level + 1, 2)
        else:
            three_min_martingale_level = 0

    redir = admin_path(trade.market_type)
    return RedirectResponse(redir, status_code=303)

@app.post("/pause/{market}")
async def toggle_pause(market: str):
    """Pause closes the session in the Telegram group, resume starts a new one."""
    global bot_paused_patience, bot_paused_3min
    m = "patience" if market == "patience" else "3min"
    if m == "patience":
        bot_paused_patience = not bot_paused_patience
        paused = bot_paused_patience
    else:
        bot_paused_3min = not bot_paused_3min
        paused = bot_paused_3min
    token, chat_id, _ = get_token_and_chat(m)
    picture = "session_close.jpg" if paused else "session_start.jpg"
    await asyncio.get_running_loop().run_in_executor(
        None, lambda: send_telegram_photo(picture, token, chat_id, market=m))
    ENGINES[m].set_info("Session closed (bot paused)" if paused else "Session started (bot resumed)")
    return RedirectResponse(admin_path(m), status_code=303)

@app.post("/toggle-auto/{market}")
async def toggle_auto(market: str):
    global auto_scan_patience, auto_scan_3min
    if market == "patience":
        auto_scan_patience = not auto_scan_patience
        return RedirectResponse("/admin/patience", status_code=303)
    else:
        auto_scan_3min = not auto_scan_3min
        return RedirectResponse("/admin/3min", status_code=303)

# ---- public site, accounts and user dashboard ------------------------------
login_throttle = auth.Throttle(limit=8, window=900)
signup_throttle = auth.Throttle(limit=30, window=3600)
_stats_cache = {"at": None, "data": None}
RESOLVED = ["win", "loss", "draw"]

def site_stats(db):
    """Real numbers for the home page, cached for 5 minutes."""
    now = datetime.datetime.utcnow()
    if _stats_cache["at"] and (now - _stats_cache["at"]).total_seconds() < 300:
        return _stats_cache["data"]
    wins = db.query(Trade).filter(Trade.status == "win").count()
    losses = db.query(Trade).filter(Trade.status == "loss").count()
    draws = db.query(Trade).filter(Trade.status == "draw").count()
    live = db.query(Trade).filter(Trade.status == "active").count()
    data = {"wins": wins, "losses": losses, "decided": wins + losses + draws,
            "signals": wins + losses + draws + live}
    _stats_cache.update(at=now, data=data)
    return data

def current_user(request: Request, db: Session):
    uid = request.session.get("uid")
    if not uid:
        return None
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        request.session.clear()
    return user

def _as_utc(dt):
    if dt is None:
        return datetime.datetime.now(datetime.timezone.utc)
    return dt.replace(tzinfo=datetime.timezone.utc) if dt.tzinfo is None else dt

def public_signal(t: Trade) -> dict:
    """Only what members should see: no scoring details, no AI notes."""
    d = t.details or {}
    posted = d.get("activated_at") or _as_utc(t.created_at).isoformat()
    if d.get("entry_at") and d.get("expire_at"):
        entry, expire = d["entry_at"], d["expire_at"]
        mart_entry, mart_expire = d.get("mart_entry_at"), d.get("mart_expire_at")
    else:  # signals saved before member accounts existed
        base = datetime.datetime.fromisoformat(posted)
        e = base + datetime.timedelta(minutes=1)
        x = e + datetime.timedelta(minutes=t.expiry_mins)
        me = x + datetime.timedelta(minutes=1)
        entry, expire, mart_entry = e.isoformat(), x.isoformat(), me.isoformat()
        mart_expire = (me + datetime.timedelta(minutes=t.expiry_mins)).isoformat()
    return {
        "id": t.id, "market": t.market_type, "trade_number": t.trade_number, "asset": t.asset,
        "action": t.action, "expiry_mins": t.expiry_mins, "status": t.status,
        "martingale_level": t.martingale_level or 0, "posted_at": posted,
        "entry_at": entry, "expire_at": expire, "mart_entry_at": mart_entry, "mart_expire_at": mart_expire,
    }

@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    signed_in = bool(request.session.get("uid") or request.session.get("admin"))
    return HTMLResponse(ui.landing_page(signed_in, site_stats(db)))

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    if request.session.get("uid"):
        return RedirectResponse("/app", status_code=303)
    return HTMLResponse(ui.auth_page("signup"))

@app.post("/signup", response_class=HTMLResponse)
async def signup_submit(request: Request, full_name: str = Form(""), username: str = Form(""),
                        email: str = Form(""), password: str = Form(""),
                        confirm: str = Form(""), db: Session = Depends(get_db)):
    full_name = auth.clean_name(full_name)
    username = auth.clean_username(username)
    email = auth.clean_email(email)
    def fail(message):
        return HTMLResponse(ui.auth_page("signup", error=message, email=email, full_name=full_name, username=username))
    if signup_throttle.blocked("all"):
        return fail("Too many sign ups right now. Please try again later.")
    signup_throttle.fail("all")
    problem = auth.name_problem(full_name) or auth.username_problem(username)
    if problem:
        return fail(problem)
    if not auth.valid_email(email):
        return fail("Please enter a valid email address.")
    problem = auth.password_problem(password)
    if problem:
        return fail(problem)
    if password != confirm:
        return fail("The two passwords do not match.")
    if db.query(User).filter(User.username == username).first():
        return fail("That username is taken. Please choose another.")
    if db.query(User).filter(User.email == email).first():
        return fail("An account with this email already exists. Try logging in.")
    user = User(email=email, full_name=full_name, username=username,
                password_hash=auth.hash_password(password), is_active=not REQUIRE_APPROVAL)
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception as e:
        print(f"[SIGNUP] {e}")
        db.rollback()
        return fail("Could not create the account. The username or email may already be used.")
    if not user.is_active:
        return HTMLResponse(ui.auth_page("login", notice="Account created. The admin needs to switch it on before you can see signals.", email=email))
    request.session.clear()
    request.session["uid"] = user.id
    return RedirectResponse("/app", status_code=303)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get("uid"):
        return RedirectResponse("/app", status_code=303)
    return HTMLResponse(ui.auth_page("login"))

@app.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, email: str = Form(""), password: str = Form(""),
                       db: Session = Depends(get_db)):
    email = (email or "").strip()
    who = auth.clean_email(email) if "@" in email else auth.clean_username(email)
    key = f"user:{who}"
    def fail(message):
        return HTMLResponse(ui.auth_page("login", error=message, email=email))
    if login_throttle.blocked(key):
        return fail("Too many attempts. Please wait a few minutes and try again.")
    if "@" in email:
        user = db.query(User).filter(User.email == who).first()
    else:
        user = db.query(User).filter(User.username == who).first()
    if not user or not auth.verify_password(password, user.password_hash):
        login_throttle.fail(key)
        return fail("Incorrect email/username or password.")
    login_throttle.clear(key)
    if user.is_active is False:
        return HTMLResponse(ui.pending_page(user.email))
    request.session.clear()
    request.session["uid"] = user.id
    return RedirectResponse("/app", status_code=303)

@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user.username and user.full_name:
        return RedirectResponse("/app", status_code=303)
    return HTMLResponse(ui.profile_page(user.email, full_name=user.full_name or "", username=user.username or ""))

@app.post("/profile", response_class=HTMLResponse)
async def profile_submit(request: Request, full_name: str = Form(""), username: str = Form(""),
                         db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    full_name = auth.clean_name(full_name)
    username = auth.clean_username(username)
    def fail(message):
        return HTMLResponse(ui.profile_page(user.email, error=message, full_name=full_name, username=username))
    problem = auth.name_problem(full_name) or auth.username_problem(username)
    if problem:
        return fail(problem)
    taken = db.query(User).filter(User.username == username).first()
    if taken and taken.id != user.id:
        return fail("That username is taken. Please choose another.")
    user.full_name = full_name
    user.username = username
    try:
        db.commit()
    except Exception as e:
        print(f"[PROFILE] {e}")
        db.rollback()
        return fail("Could not save your details. Please try again.")
    return RedirectResponse("/app", status_code=303)

@app.get("/app", response_class=HTMLResponse)
async def user_app(request: Request, db: Session = Depends(get_db)):
    if request.session.get("admin"):
        return HTMLResponse(ui.user_dashboard("Admin", chat_name="Admin"))
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user.is_active is False:
        return HTMLResponse(ui.pending_page(user.email))
    if not user.username or not user.full_name:
        return RedirectResponse("/profile", status_code=303)
    return HTMLResponse(ui.user_dashboard(user.email, chat_name=user.username))

@app.get("/api/signals")
async def api_signals(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("admin"):
        user = current_user(request, db)
        if not user:
            return JSONResponse({"error": "login required"}, status_code=401)
        if user.is_active is False:
            return JSONResponse({"error": "account not active"}, status_code=403)
    live_states = ["active"] + RESOLVED
    rows = []
    for m in ("patience", "3min"):   # each bot gets its own latest results
        rows += db.query(Trade).filter(Trade.market_type == m, Trade.status.in_(live_states)).order_by(Trade.id.desc()).limit(25).all()
    week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    recent = db.query(Trade).filter(Trade.status.in_(RESOLVED), Trade.created_at >= week_ago).all()
    stats = {m: {"wins": 0, "losses": 0, "draws": 0} for m in ("patience", "3min")}
    for t in recent:
        bucket = stats.get(t.market_type)
        if bucket is not None:
            bucket[{"win": "wins", "loss": "losses", "draw": "draws"}[t.status]] += 1
    return JSONResponse({
        "server_now": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "signals": [public_signal(t) for t in rows],
        "stats": stats,
    })

# ---- community chat ----------------------------------------------------------
chat_rate = auth.Throttle(limit=20, window=60)     # at most 20 messages a minute each
chat_last = {}                                      # last message time per author
CHAT_MAX_CHARS = 400
CHAT_HISTORY = 60

def chat_viewer(request: Request, db: Session):
    """Returns (user, is_admin, error_response). Members need an active account with a username."""
    if request.session.get("admin"):
        return None, True, None
    user = current_user(request, db)
    if not user:
        return None, False, JSONResponse({"error": "login required"}, status_code=401)
    if user.is_active is False:
        return None, False, JSONResponse({"error": "account not active"}, status_code=403)
    if not user.username:
        return None, False, JSONResponse({"error": "choose a username first"}, status_code=403)
    return user, False, None

@app.get("/api/chat")
async def chat_list(request: Request, db: Session = Depends(get_db)):
    user, is_admin, error = chat_viewer(request, db)
    if error:
        return error
    rows = db.query(ChatMessage).order_by(ChatMessage.id.desc()).limit(CHAT_HISTORY).all()
    rows.reverse()
    messages = [{
        "id": m.id, "username": m.username, "is_admin": bool(m.is_admin), "text": m.text,
        "at": _as_utc(m.created_at).isoformat(),
        "mine": (is_admin and bool(m.is_admin)) or (user is not None and m.user_id == user.id and not m.is_admin),
    } for m in rows]
    return JSONResponse({"messages": messages, "muted": bool(user and user.is_muted), "admin": is_admin})

@app.post("/api/chat")
async def chat_send(request: Request, db: Session = Depends(get_db)):
    user, is_admin, error = chat_viewer(request, db)
    if error:
        return error
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    text = auth.clean_chat_text(str(payload.get("text", "")) if isinstance(payload, dict) else "")
    if not text:
        return JSONResponse({"error": "Type a message first."}, status_code=400)
    if len(text) > CHAT_MAX_CHARS:
        return JSONResponse({"error": f"Messages can be up to {CHAT_MAX_CHARS} characters."}, status_code=400)
    if not is_admin:
        if user.is_muted:
            return JSONResponse({"error": "You have been muted by the admin."}, status_code=403)
        if auth.has_link(text):
            return JSONResponse({"error": "Links are not allowed in chat."}, status_code=400)
        key = f"u{user.id}"
        now = datetime.datetime.utcnow()
        last = chat_last.get(key)
        if chat_rate.blocked(key) or (last and (now - last).total_seconds() < 1.5):
            return JSONResponse({"error": "You are sending messages too fast. Slow down."}, status_code=429)
        chat_rate.fail(key)
        chat_last[key] = now
    message = ChatMessage(
        user_id=None if is_admin else user.id,
        username="Admin" if is_admin else user.username,
        is_admin=is_admin, text=text,
    )
    db.add(message)
    db.commit()
    return JSONResponse({"ok": True})

@app.get("/admin/chat", response_class=HTMLResponse)
async def admin_chat():
    return HTMLResponse(ui.admin_chat_page())

@app.post("/admin/chat/{message_id}/delete")
async def admin_chat_delete(message_id: int, db: Session = Depends(get_db)):
    message = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    if message:
        db.delete(message)
        db.commit()
    return JSONResponse({"ok": True})

# ---- admin ---------------------------------------------------------------
admin_throttle = auth.Throttle(limit=6, window=900)

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    if request.session.get("admin"):
        return RedirectResponse("/admin", status_code=303)
    return HTMLResponse(ui.admin_login_page(not_configured=not auth.admin_configured(ADMIN_PASSWORD)))

@app.post("/admin/login", response_class=HTMLResponse)
async def admin_login_submit(request: Request, username: str = Form(""), password: str = Form("")):
    if not auth.admin_configured(ADMIN_PASSWORD):
        return HTMLResponse(ui.admin_login_page(not_configured=True))
    if admin_throttle.blocked("admin"):
        return HTMLResponse(ui.admin_login_page(error="Too many attempts. Wait a few minutes and try again."))
    if not auth.admin_credentials_ok(username, password, ADMIN_USERNAME, ADMIN_PASSWORD):
        admin_throttle.fail("admin")
        return HTMLResponse(ui.admin_login_page(error="Incorrect username or password."))
    admin_throttle.clear("admin")
    request.session.clear()
    request.session["admin"] = True
    return RedirectResponse("/admin", status_code=303)

@app.get("/admin", response_class=HTMLResponse)
async def admin_home(db: Session = Depends(get_db)):
    users = db.query(User).all()
    waiting = len([u for u in users if u.is_active is False])
    info = {m: f"{e.last_scan_info} · {telegram_status.get(m, '')}" for m, e in ENGINES.items()}
    return HTMLResponse(ui.admin_hub(len(users), waiting, REQUIRE_APPROVAL, info))

@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users(db: Session = Depends(get_db)):
    rows = db.query(User).order_by(User.id.desc()).all()
    users = [{"id": u.id, "email": u.email, "is_active": u.is_active is not False,
              "full_name": u.full_name or "", "username": u.username or "",
              "is_muted": bool(u.is_muted),
              "joined": u.created_at.strftime("%d %b %Y") if u.created_at else "-"} for u in rows]
    return HTMLResponse(ui.admin_users_page(users, REQUIRE_APPROVAL))

@app.post("/admin/users/{user_id}/toggle")
async def admin_toggle_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.is_active = not (user.is_active is not False)
        db.commit()
    return RedirectResponse("/admin/users", status_code=303)

@app.post("/admin/users/{user_id}/mute")
async def admin_mute_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.is_muted = not bool(user.is_muted)
        db.commit()
    return RedirectResponse("/admin/users", status_code=303)

@app.post("/admin/telegram-test/{market}")
async def telegram_test(market: str):
    m = "3min" if market == "3min" else "patience"
    token, chat_id, _ = get_token_and_chat(m)
    await asyncio.get_running_loop().run_in_executor(
        None, lambda: send_telegram(f"Test message from DH Binary Trader ({ENGINES[m].name}). Telegram is connected.", token, chat_id, market=m))
    return RedirectResponse(admin_path(m), status_code=303)

# Old bookmarks
@app.get("/patience")
async def old_patience():
    return RedirectResponse("/admin/patience", status_code=303)

@app.get("/3min")
async def old_three_min():
    return RedirectResponse("/admin/3min", status_code=303)

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
                send_telegram("TRADING PAUSED - HIGH IMPACT NEWS!\n" + "\n".join(lines) + f"\n\nResume at: {safe_str}", token, chat_id, market=market)
                if personal_id:
                    send_telegram(f"News! Signals paused.\nSafe after: {safe_str}", token, personal_id)
            return
        if news_warned[market]:
            news_warned[market] = False
            send_telegram("News over! Signals resuming...", token, chat_id, market=market)
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
                    engine.set_info(f"Legacy signal #{open_trade.trade_number} is pending manual posting or skip")
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
            # Publish immediately: no admin approval or click-to-activate delay.
            now = datetime.datetime.now(WAT)
            entry = now + datetime.timedelta(minutes=1)
            expire = entry + datetime.timedelta(minutes=expiry)
            mart_entry = expire + datetime.timedelta(minutes=1)
            mart_expire = mart_entry + datetime.timedelta(minutes=expiry)
            data.update({k: v.astimezone(datetime.timezone.utc).isoformat() for k, v in {
                "activated_at": now, "entry_at": entry, "expire_at": expire,
                "mart_entry_at": mart_entry, "mart_expire_at": mart_expire}.items()})
            trade = Trade(
                trade_number=tnum, asset=asset, action=direction, expiry_mins=expiry,
                price=data["price"], confidence="High", status="active", details=data,
                market_type=market, martingale_level=level, is_martingale=level > 0,
            )
            db.add(trade)
            db.commit()
            db.refresh(trade)
            posted = send_telegram(build_signal_message(trade, now), token, chat_id, market=market)
            details = dict(trade.details or {})
            details["telegram_posted"] = bool(posted)
            details["telegram_posted_at"] = now.astimezone(datetime.timezone.utc).isoformat() if posted else None
            trade.details = details
            db.commit()
            engine.set_info(
                f"Signal #{tnum} {asset} {direction} published to Telegram" if posted
                else f"Signal #{tnum} {asset} {direction} generated, but Telegram posting failed"
            )
            print(f"[{engine.name}] SIGNAL {asset} {direction} {expiry}min | Telegram: {'OK' if posted else 'FAILED'}")
            if personal_id:
                send_telegram(
                    f"{engine.name}: signal {'published' if posted else 'generated; group post failed'}\n"
                    f"{asset} {direction} ({expiry} min).\n"
                    f"Use Skip in the admin dashboard if you do not want to track this trade.",
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
            "telegram": telegram_status.get(market),
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
        engine.group_notifier = lambda text, t=token, c=chat_id, m=market: send_telegram(text, t, c, market=m)
    asyncio.create_task(background_scanner())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
