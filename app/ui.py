"""HTML pages for DH Binary Trader (landing, accounts, user dashboard, admin)."""
import datetime
import html

from .ui_css import CSS, LOGO_MARK, SITE

RISK_TEXT = (
    "Binary options trading carries a high risk of losing your capital and is restricted or illegal in some "
    "countries. Signals are information only, not financial advice, and past results do not guarantee future "
    "performance. Only trade money you can afford to lose, and check the rules where you live."
)


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def head(title: str, extra: str = "") -> str:
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="theme-color" content="#070a12">'
        f"<title>{esc(title)}</title><style>{CSS}</style>{extra}</head>"
    )


def logo(href: str = "/") -> str:
    return (f'<a class="logo" href="{href}">{LOGO_MARK}'
            f'<span>DH Binary Trader<small>Live signals</small></span></a>')


def topbar(right: str, links: str = "") -> str:
    return (f'<header class="topbar"><div class="wrap">{logo()}'
            f'<nav class="navlinks">{links}{right}</nav></div></header>')


def footer() -> str:
    year = datetime.datetime.now().year
    return (f'<footer class="site"><div class="wrap">'
            f'<div class="logo">{LOGO_MARK}<span>{SITE}</span></div>'
            f'<p>{esc(RISK_TEXT)}</p><p>&copy; {year} {SITE}. All rights reserved.</p></div></footer>')


# --------------------------------------------------------------------- landing
def landing_page(signed_in: bool = False, stats: dict = None) -> str:
    if signed_in:
        nav_right = '<a class="btn btn-primary btn-sm" href="/app">Open dashboard</a>'
        hero_cta = '<a class="btn btn-primary btn-lg" href="/app">Open my dashboard</a>'
        band_cta = '<a class="btn btn-primary btn-lg" href="/app">Go to my signals</a>'
    else:
        nav_right = ('<a class="btn btn-ghost btn-sm" href="/login">Log in</a>'
                     '<a class="btn btn-primary btn-sm" href="/signup">Get started</a>')
        hero_cta = ('<a class="btn btn-primary btn-lg" href="/signup">Create free account</a>'
                    '<a class="btn btn-ghost btn-lg" href="#how">How it works</a>')
        band_cta = '<a class="btn btn-primary btn-lg" href="/signup">Create your account</a>'

    links = '<a class="link" href="#how">How it works</a><a class="link" href="#bots">Our bots</a><a class="link" href="#safety">Safeguards</a>'

    strip = ""
    if stats and stats.get("decided", 0) >= 30:
        decided = stats["wins"] + stats["losses"]
        rate = round(stats["wins"] * 100 / decided) if decided else 0
        strip = (
            '<section class="section" style="padding:10px 0 0"><div class="wrap"><div class="strip">'
            f'<div class="card"><b>{stats["signals"]}</b><span>Signals posted</span></div>'
            f'<div class="card"><b>{stats["wins"]}</b><span>Wins logged</span></div>'
            f'<div class="card"><b>{stats["losses"]}</b><span>Losses logged</span></div>'
            f'<div class="card"><b>{rate}%</b><span>Win rate (excl. draws)</span></div>'
            '</div></div></section>'
        )

    body = f"""
{topbar(nav_right, links)}
<main>
<section class="hero"><div class="wrap hero-grid">
  <div>
    <span class="pill"><span class="dot"></span> Live signals during the London &amp; Tokyo sessions</span>
    <h1 class="hero-title">Binary options signals, <span class="grad-text">filtered before they reach you.</span></h1>
    <p class="lead">{SITE} scans 17 forex pairs every minute, checks three timeframes and an AI review, then drops only the strongest setups straight to your dashboard.</p>
    <div class="cta-row">{hero_cta}</div>
    <div class="trust"><span>17 pairs scanned</span><span>M1 + M5 + M15 checks</span><span>AI confirmed</span><span>News filter</span></div>
  </div>
  <div class="mock">
    <span class="mock-tag">Sample signal</span>
    <div class="sig-head"><span><span class="dot" style="display:inline-block;margin-right:7px"></span>LIVE &middot; Patience Bot</span><span>Trade #24</span></div>
    <div class="sig-main"><div class="asset">EUR/USD</div><div class="dir buy">&#9650; BUY</div></div>
    <div class="sig-grid">
      <div><small>Entry</small><b>11:25 AM</b></div>
      <div><small>Expiry</small><b>11:28 AM</b></div>
      <div><small>Duration</small><b>3 min</b></div>
    </div>
    <div class="sig-foot">Optional martingale if it loses: enter 11:29 AM, double stake.</div>
  </div>
</div></section>

{strip}

<section class="section" id="how"><div class="wrap">
  <div class="eyebrow">How it works</div>
  <h2>From account to signal in three steps</h2>
  <p class="sub">No Telegram juggling. Your signals appear the moment they are approved, with the entry and expiry times ready.</p>
  <div class="grid3">
    <div class="card"><div class="step-n">1</div><h3>Create your account</h3><p>Sign up with your email and a password. It takes under a minute.</p></div>
    <div class="card"><div class="step-n">2</div><h3>Keep your dashboard open</h3><p>New signals drop in live with a sound alert, an entry countdown and the exact expiry time.</p></div>
    <div class="card"><div class="step-n">3</div><h3>Trade at the entry time</h3><p>Place the trade on your platform, and follow the optional martingale plan if you use one.</p></div>
  </div>
</div></section>

<section class="section" id="bots"><div class="wrap">
  <div class="eyebrow">Our bots</div>
  <h2>Two bots, two trading styles</h2>
  <p class="sub">Both run all day and only post when a setup passes every check.</p>
  <div class="grid2">
    <div class="card bot-card"><span class="tag g">Patience Bot</span><h3>Fewer signals, higher standards</h3>
      <p>Waits for a setup to line up across indicators, candle patterns and higher timeframes before posting.</p>
      <ul class="ticks"><li>Trades only in good and excellent sessions</li><li>Expiry of 2 to 5 minutes picked per setup</li><li>Pairs rest after wins and losses</li></ul></div>
    <div class="card bot-card"><span class="tag b">3 min Bot</span><h3>Volatility aware and faster</h3>
      <p>Watches market volatility and switches to a stricter mode when prices get wild.</p>
      <ul class="ticks"><li>Strict mode during high volatility</li><li>Structured martingale plan, up to 2 levels</li><li>Short cooldown between signals</li></ul></div>
  </div>
</div></section>

<section class="section" id="safety"><div class="wrap">
  <div class="eyebrow">Safeguards</div>
  <h2>Built to skip the bad setups</h2>
  <p class="sub">Most of the work is deciding what not to signal.</p>
  <div class="grid3">
    <div class="card"><h3>Three timeframe check</h3><p>Every setup must agree on the 1, 5 and 15 minute charts before it moves on.</p></div>
    <div class="card"><h3>Choppy market filter</h3><p>Flat, zigzag and low momentum markets are rejected automatically.</p></div>
    <div class="card"><h3>AI review</h3><p>Each shortlist is reviewed by an AI analyst that must be highly confident to approve.</p></div>
    <div class="card"><h3>News protection</h3><p>Signals pause around high impact news events.</p></div>
    <div class="card"><h3>Loss protection</h3><p>After consecutive losses the bot pauses, and losing pairs are banned for a while.</p></div>
    <div class="card"><h3>Session quality</h3><p>Low quality hours are skipped, so you are not chasing signals in thin markets.</p></div>
  </div>
</div></section>

<section class="section" style="padding-top:20px"><div class="wrap">
  <div class="cta-band"><h2>Ready to see the next signal?</h2>
  <p class="sub" style="margin:0 auto 22px">Create your account and keep your dashboard open during the trading sessions.</p>{band_cta}</div>
</div></section>
</main>
{footer()}
</body></html>"""
    return head(f"{SITE} | Live binary options signals") + "<body>" + body


# ------------------------------------------------------------------ auth pages
def auth_page(mode: str, error: str = "", email: str = "", notice: str = "") -> str:
    signup = mode == "signup"
    title = "Create your account" if signup else "Welcome back"
    sub = ("Sign up with your email to get live signals on your dashboard."
           if signup else "Log in to see your live signals.")
    msg = ""
    if error:
        msg += f'<div class="msg err">{esc(error)}</div>'
    if notice:
        msg += f'<div class="msg ok">{esc(notice)}</div>'
    confirm = ('<label for="confirm">Confirm password</label>'
               '<input id="confirm" name="confirm" type="password" autocomplete="new-password" required>'
               if signup else "")
    pw_auto = "new-password" if signup else "current-password"
    button = "Create account" if signup else "Log in"
    alt = ('Already have an account? <a href="/login">Log in</a>' if signup
           else 'New here? <a href="/signup">Create an account</a>')
    body = f"""
{topbar('<a class="btn btn-ghost btn-sm" href="/">Home</a>')}
<main class="auth-wrap"><div class="auth-card">
  <h1>{title}</h1><p class="sub">{sub}</p>{msg}
  <form method="post" action="/{mode}">
    <label for="email">Email</label>
    <input id="email" name="email" type="email" value="{esc(email)}" autocomplete="email" required>
    <label for="password">Password</label>
    <input id="password" name="password" type="password" autocomplete="{pw_auto}" required>
    {confirm}
    <button class="btn btn-primary" type="submit">{button}</button>
  </form>
  <p class="alt">{alt}</p>
</div></main></body></html>"""
    return head(f"{title} | {SITE}") + "<body>" + body


def admin_login_page(error: str = "", not_configured: bool = False) -> str:
    msg = ""
    if not_configured:
        msg = ('<div class="msg err">Admin login is switched off. Set the ADMIN_USERNAME and ADMIN_PASSWORD '
               'environment variables in Render (not the default password), then redeploy.</div>')
    elif error:
        msg = f'<div class="msg err">{esc(error)}</div>'
    body = f"""
{topbar('<a class="btn btn-ghost btn-sm" href="/">Home</a>')}
<main class="auth-wrap"><div class="auth-card">
  <h1>Admin login</h1><p class="sub">Owner access to the bot controls.</p>{msg}
  <form method="post" action="/admin/login">
    <label for="u">Username</label><input id="u" name="username" type="text" autocomplete="username" required>
    <label for="p">Password</label><input id="p" name="password" type="password" autocomplete="current-password" required>
    <button class="btn btn-primary" type="submit">Log in</button>
  </form>
</div></main></body></html>"""
    return head(f"Admin login | {SITE}") + "<body>" + body


# ------------------------------------------------------------- user dashboard
DASH_JS = r"""
(function(){
  var offset = 0, seen = null, filter = 'all', lastJson = '', soundOn = true, flashTimer = null;
  var timeFmt = new Intl.DateTimeFormat('en-US', {hour:'numeric', minute:'2-digit', hour12:true, timeZone:'Africa/Lagos'});
  var BOT = {patience:'Patience Bot', '3min':'3 min Bot'};
  function esc(s){ return String(s).replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
  function t(iso){ return iso ? timeFmt.format(new Date(iso)) + ' WAT' : '-'; }
  function now(){ return Date.now() + offset; }
  function mmss(ms){ var s = Math.max(0, Math.round(ms/1000)), m = Math.floor(s/60); return m + ':' + ('0' + (s%60)).slice(-2); }

  function liveCard(s){
    var dir = s.action === 'BUY' ? 'buy' : 'sell', arrow = s.action === 'BUY' ? '&#9650;' : '&#9660;';
    var mg = s.martingale_level ? ' &middot; Martingale ' + s.martingale_level : '';
    return '<div class="live-card ' + dir + '">' +
      '<div class="sig-head"><span><span class="chip live">Live</span> &nbsp;' + esc(BOT[s.market] || s.market) + mg + '</span><span>Trade #' + esc(s.trade_number) + '</span></div>' +
      '<div class="sig-main"><div class="asset">' + esc(s.asset) + '</div><div class="dir ' + dir + '">' + arrow + ' ' + esc(s.action) + '</div></div>' +
      '<div class="sig-grid"><div><small>Entry</small><b>' + t(s.entry_at) + '</b></div><div><small>Expiry</small><b>' + t(s.expire_at) + '</b></div><div><small>Duration</small><b>' + esc(s.expiry_mins) + ' min</b></div></div>' +
      '<div class="countdown" data-entry="' + esc(s.entry_at||'') + '" data-exp="' + esc(s.expire_at||'') + '">...</div>' +
      '<div class="mart">If it loses, optional martingale: enter ' + t(s.mart_entry_at) + ', expires ' + t(s.mart_expire_at) + ', double the stake.</div></div>';
  }
  function resultChip(s){
    if (s.status === 'win') return '<span class="chip win">Win</span>';
    if (s.status === 'loss') return '<span class="chip loss">Loss</span>';
    if (s.status === 'draw') return '<span class="chip draw">Draw</span>';
    return '<span class="chip wait">Open</span>';
  }
  function row(s){
    var dir = s.action === 'BUY' ? 'buy' : 'sell', arrow = s.action === 'BUY' ? '&#9650;' : '&#9660;';
    return '<div class="row"><div class="t">' + t(s.posted_at).replace(' WAT','') + '</div>' +
      '<div class="a"><b>' + esc(s.asset) + '</b><small>' + esc(BOT[s.market] || s.market) + ' &middot; ' + esc(s.expiry_mins) + ' min</small></div>' +
      '<div class="d ' + dir + '">' + arrow + ' ' + esc(s.action) + '</div><div>' + resultChip(s) + '</div></div>';
  }
  function statBox(name, st){
    var dec = st.wins + st.losses, rate = dec ? Math.round(st.wins * 100 / dec) + '%' : '-';
    return '<div class="statbox"><small>' + name + ' &middot; last 7 days</small><div class="num">' + rate +
      '<span>' + st.wins + 'W &middot; ' + st.losses + 'L &middot; ' + st.draws + 'D</span></div></div>';
  }

  function render(d){
    var open = d.signals.filter(function(s){ return s.status === 'active'; });
    var live = document.getElementById('live');
    live.innerHTML = open.length ? open.map(liveCard).join('') :
      '<div class="waiting"><div class="radar"></div><b style="color:var(--text)">Waiting for the next signal</b><br>The bots are scanning the market. This page updates by itself.</div>';
    var list = d.signals.filter(function(s){ return filter === 'all' || s.market === filter; });
    document.getElementById('feed').innerHTML = list.length ? list.map(row).join('') : '<div class="empty">No signals yet.</div>';
    document.getElementById('stats').innerHTML = statBox('Patience Bot', d.stats.patience) + statBox('3 min Bot', d.stats['3min']);
    tick();
  }
  function tick(){
    var els = document.querySelectorAll('.countdown');
    for (var i = 0; i < els.length; i++){
      var e = els[i], en = Date.parse(e.dataset.entry), ex = Date.parse(e.dataset.exp), n = now(), txt;
      if (n < en) txt = 'Enter in ' + mmss(en - n);
      else if (n < ex) txt = 'In trade &middot; expires in ' + mmss(ex - n);
      else txt = 'Expired &middot; waiting for the result';
      e.innerHTML = txt;
    }
  }
  function beep(){
    try{
      var C = window.AudioContext || window.webkitAudioContext, c = new C(), o = c.createOscillator(), g = c.createGain();
      o.type = 'sine'; o.frequency.value = 880; o.connect(g); g.connect(c.destination);
      g.gain.setValueAtTime(0.0001, c.currentTime); g.gain.exponentialRampToValueAtTime(0.3, c.currentTime + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, c.currentTime + 0.6); o.start(); o.stop(c.currentTime + 0.65);
    }catch(e){}
  }
  function alertNew(s){
    if (soundOn) beep();
    try{ if (navigator.vibrate) navigator.vibrate([200,100,200]); }catch(e){}
    var base = document.title, on = false, n = 0;
    clearInterval(flashTimer);
    flashTimer = setInterval(function(){ on = !on; document.title = on ? 'NEW SIGNAL ' + s.asset : base; if (++n > 12){ clearInterval(flashTimer); document.title = base; } }, 700);
    try{ if (window.Notification && Notification.permission === 'granted') new Notification('New signal: ' + s.asset + ' ' + s.action, {body: s.expiry_mins + ' minute trade. Open the dashboard for entry time.'}); }catch(e){}
  }
  function poll(){
    fetch('/api/signals', {credentials:'same-origin', cache:'no-store'}).then(function(r){
      if (r.status === 401 || r.status === 403){ location.href = '/login'; return null; }
      return r.json();
    }).then(function(d){
      if (!d) return;
      offset = Date.parse(d.server_now) - Date.now();
      var ids = d.signals.map(function(s){ return s.id; });
      if (seen !== null){ d.signals.forEach(function(s){ if (s.status === 'active' && seen.indexOf(s.id) < 0) alertNew(s); }); }
      seen = ids;
      var j = JSON.stringify(d.signals) + JSON.stringify(d.stats);
      if (j !== lastJson){ lastJson = j; window.__d = d; render(d); }
      document.getElementById('conn').textContent = 'Live';
    }).catch(function(){ document.getElementById('conn').textContent = 'Reconnecting...'; });
  }
  document.getElementById('tabs').addEventListener('click', function(ev){
    var b = ev.target.closest('.tab'); if (!b) return;
    filter = b.dataset.f;
    var all = document.querySelectorAll('.tab'); for (var i = 0; i < all.length; i++) all[i].classList.remove('on');
    b.classList.add('on'); if (window.__d) render(window.__d);
  });
  document.getElementById('alerts').addEventListener('click', function(){
    soundOn = !soundOn; this.textContent = soundOn ? 'Sound on' : 'Sound off';
    if (soundOn) beep();
    try{ if (window.Notification && Notification.permission === 'default') Notification.requestPermission(); }catch(e){}
  });
  setInterval(tick, 1000); setInterval(poll, 4000); poll();
})();
"""


def user_dashboard(email: str) -> str:
    right = ('<form method="post" action="/logout" style="display:inline">'
             '<button class="linkbtn" type="submit">Log out</button></form>')
    body = f"""
{topbar(right)}
<main class="dash"><div class="wrap">
  <div class="dash-head">
    <div><h1>Live signals</h1><p>Signed in as {esc(email)} &middot; <span id="conn">Connecting...</span></p></div>
    <div class="tools"><button id="alerts" class="btn btn-ghost btn-sm" type="button">Sound on</button></div>
  </div>
  <div class="statrow" id="stats"></div>
  <div class="sec-title">Live now</div>
  <div id="live"></div>
  <div class="sec-title">Recent signals</div>
  <div class="tabs" id="tabs">
    <button class="tab on" data-f="all" type="button">All</button>
    <button class="tab" data-f="patience" type="button">Patience Bot</button>
    <button class="tab" data-f="3min" type="button">3 min Bot</button>
  </div>
  <div class="feed" id="feed"><div class="empty">Loading...</div></div>
  <p class="fine">Times are shown in WAT. Place the trade at the entry time. {esc(RISK_TEXT)}</p>
</div></main>
<script>{DASH_JS}</script>
</body></html>"""
    return head(f"Dashboard | {SITE}") + "<body>" + body


def pending_page(email: str) -> str:
    right = ('<form method="post" action="/logout" style="display:inline">'
             '<button class="linkbtn" type="submit">Log out</button></form>')
    body = f"""
{topbar(right)}
<main class="auth-wrap"><div class="auth-card" style="text-align:center">
  <h1>Account waiting for approval</h1>
  <p class="sub">Thanks for signing up with {esc(email)}. Your access has not been switched on yet. Please contact the admin to activate your account, then log in again.</p>
  <a class="btn btn-ghost" href="/">Back to home</a>
</div></main></body></html>"""
    return head(f"Approval needed | {SITE}") + "<body>" + body


# ---------------------------------------------------------------------- admin
def admin_hub(user_count: int, waiting: int, require_approval: bool, bot_info: dict) -> str:
    right = ('<a class="btn btn-ghost btn-sm" href="/app">User view</a>'
             '<form method="post" action="/logout" style="display:inline"><button class="linkbtn" type="submit">Log out</button></form>')
    def bot_card(path, name, key):
        info = esc(bot_info.get(key, ""))
        return (f'<a class="card hub-card" href="{path}"><h3>{name} controls</h3>'
                f'<p>Scan, activate signals, log results.</p><p style="margin-top:10px;font-size:.82rem">{info}</p></a>')
    approval = "Approval required for new accounts" if require_approval else "New accounts get access straight away"
    body = f"""
{topbar(right)}
<main class="dash"><div class="wrap">
  <div class="dash-head"><div><h1>Admin</h1><p>{esc(approval)}</p></div></div>
  <div class="grid3">
    {bot_card("/admin/patience", "Patience Bot", "patience")}
    {bot_card("/admin/3min", "3 min Bot", "3min")}
    <a class="card hub-card" href="/admin/users"><h3>Members</h3>
      <p>{user_count} account(s){f", {waiting} waiting for approval" if waiting else ""}</p>
      <p style="margin-top:10px;font-size:.82rem">Enable or disable access.</p></a>
  </div>
  <p class="fine"><a href="/status" style="text-decoration:underline">Price data and bot status (JSON)</a></p>
</div></main></body></html>"""
    return head(f"Admin | {SITE}") + "<body>" + body


def admin_users_page(users: list, require_approval: bool, message: str = "") -> str:
    right = '<a class="btn btn-ghost btn-sm" href="/admin">Back</a>'
    rows = ""
    for u in users:
        active = bool(u["is_active"])
        chip = '<span class="chip win">Active</span>' if active else '<span class="chip wait">Disabled</span>'
        btn = (f'<button class="btn btn-sm btn-danger" type="submit">Disable</button>' if active
               else f'<button class="btn btn-sm btn-ok" type="submit">Enable</button>')
        rows += (f'<tr><td>{esc(u["email"])}</td><td>{esc(u["joined"])}</td><td>{chip}</td>'
                 f'<td><form method="post" action="/admin/users/{int(u["id"])}/toggle">{btn}</form></td></tr>')
    if not rows:
        rows = '<tr><td colspan="4" class="empty">No members yet.</td></tr>'
    note = ("New accounts start disabled. Enable them once payment is confirmed." if require_approval
            else "New accounts are active straight away. Set REQUIRE_APPROVAL=1 in Render to approve each one yourself.")
    msg = f'<div class="msg ok">{esc(message)}</div>' if message else ""
    body = f"""
{topbar(right)}
<main class="dash"><div class="wrap">
  <div class="dash-head"><div><h1>Members</h1><p>{esc(note)}</p></div></div>{msg}
  <div class="card scroll"><table class="table"><thead><tr><th>Email</th><th>Joined</th><th>Status</th><th></th></tr></thead>
  <tbody>{rows}</tbody></table></div>
</div></main></body></html>"""
    return head(f"Members | {SITE}") + "<body>" + body
