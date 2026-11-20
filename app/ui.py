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


def avatar_html(user: dict, size: int = 32) -> str:
    """Round profile picture, or a coloured circle with the first letter when there is none."""
    style = f"width:{size}px;height:{size}px;"
    if user and user.get("av"):
        return f'<img class="av" style="{style}" src="/api/avatar/{int(user["id"])}?v={int(user["av"])}" alt="">'
    letter = esc(((user or {}).get("username") or "?")[:1].upper())
    return f'<span class="av av-i" style="{style}line-height:{size}px;font-size:{round(size * 0.46)}px">{letter}</span>'


AVATAR_JS = r"""
window.dhEsc = function(s){ return String(s).replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); };
window.dhAvatar = function(u, size){
  size = size || 32;
  var st = 'width:' + size + 'px;height:' + size + 'px;';
  if (u && u.av && u.id) return '<img class="av" style="' + st + '" src="/api/avatar/' + u.id + '?v=' + u.av + '" alt="" loading="lazy">';
  var ch = ((u && u.username) || '?').charAt(0).toUpperCase();
  return '<span class="av av-i" style="' + st + 'line-height:' + size + 'px;font-size:' + Math.round(size * 0.46) + 'px">' + window.dhEsc(ch) + '</span>';
};
"""


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
def auth_page(mode: str, error: str = "", email: str = "", notice: str = "",
              full_name: str = "", username: str = "") -> str:
    signup = mode == "signup"
    title = "Create your account" if signup else "Welcome back"
    sub = ("Join DH Binary Trader to get live signals and chat with other members."
           if signup else "Log in to see your live signals.")
    msg = ""
    if error:
        msg += f'<div class="msg err">{esc(error)}</div>'
    if notice:
        msg += f'<div class="msg ok">{esc(notice)}</div>'
    if signup:
        names = (f'<label for="full_name">Full name</label>'
                 f'<input id="full_name" name="full_name" type="text" value="{esc(full_name)}" autocomplete="name" maxlength="60" required>'
                 f'<label for="username">Username</label>'
                 f'<input id="username" name="username" type="text" value="{esc(username)}" autocomplete="username" '
                 f'maxlength="20" placeholder="e.g. dh_trader" required>'
                 f'<p class="hint">This is the name other members see in chat. Letters, numbers and underscores.</p>')
        email_field = (f'<label for="email">Email</label>'
                       f'<input id="email" name="email" type="email" value="{esc(email)}" autocomplete="email" required>')
    else:
        names = ""
        email_field = (f'<label for="email">Email or username</label>'
                       f'<input id="email" name="email" type="text" value="{esc(email)}" autocomplete="username" required>')
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
    {names}
    {email_field}
    <label for="password">Password</label>
    <input id="password" name="password" type="password" autocomplete="{pw_auto}" required>
    {confirm}
    <button class="btn btn-primary" type="submit">{button}</button>
  </form>
  <p class="alt">{alt}</p>
</div></main></body></html>"""
    return head(f"{title} | {SITE}") + "<body>" + body


def profile_page(email: str, error: str = "", full_name: str = "", username: str = "") -> str:
    right = ('<form method="post" action="/logout" style="display:inline">'
             '<button class="linkbtn" type="submit">Log out</button></form>')
    msg = f'<div class="msg err">{esc(error)}</div>' if error else ""
    body = f"""
{topbar(right)}
<main class="auth-wrap"><div class="auth-card">
  <h1>Finish your profile</h1>
  <p class="sub">Add your name and pick a username to join the member chat. Signed in as {esc(email)}.</p>{msg}
  <form method="post" action="/profile">
    <label for="full_name">Full name</label>
    <input id="full_name" name="full_name" type="text" value="{esc(full_name)}" autocomplete="name" maxlength="60" required>
    <label for="username">Username</label>
    <input id="username" name="username" type="text" value="{esc(username)}" maxlength="20" placeholder="e.g. dh_trader" required>
    <p class="hint">Other members see your username in chat, never your full name or email.</p>
    <button class="btn btn-primary" type="submit">Save and continue</button>
  </form>
</div></main></body></html>"""
    return head(f"Your profile | {SITE}") + "<body>" + body


def settings_page(me: dict, full_name: str = "") -> str:
    right = ('<form method="post" action="/logout" style="display:inline">'
             '<button class="linkbtn" type="submit">Log out</button></form>')
    remove = '<button class="btn btn-ghost btn-sm" id="remove" type="button">Remove photo</button>' if me.get("av") else ""
    body = f"""
{topbar(right)}
<main class="auth-wrap"><div class="auth-card">
  <h1>Your profile</h1>
  <p class="sub">Add a profile picture. Other members see it in the chat and in private messages.</p>
  <div class="set-pic" id="pv">{avatar_html(me, 120)}</div>
  <input id="file" type="file" accept="image/*" hidden>
  <div class="set-actions">
    <button class="btn btn-ghost btn-sm" id="choose" type="button">Choose photo</button>
    <button class="btn btn-primary btn-sm" id="save" type="button" disabled>Save photo</button>
    {remove}
  </div>
  <div class="chat-note" id="pnote" style="text-align:center"></div>
  <p class="hint">Username: @{esc(me.get("username", ""))} &middot; Name: {esc(full_name)}. Other members never see your email or full name.</p>
  <a class="btn btn-ghost" href="/app" style="margin-top:12px">&larr; Back to home</a>
</div></main>
<script>{AVATAR_JS}</script>
<script>{SETTINGS_JS}</script>
</body></html>"""
    return head(f"Profile | {SITE}") + "<body>" + body


SETTINGS_JS = r"""
(function(){
  var file = document.getElementById('file'), pv = document.getElementById('pv'), save = document.getElementById('save'),
      note = document.getElementById('pnote'), remove = document.getElementById('remove'), data = null;
  function post(url, body){
    return fetch(url, {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body || {})})
      .then(function(r){ return r.json().then(function(j){ return {ok:r.ok, j:j}; }); });
  }
  document.getElementById('choose').addEventListener('click', function(){ file.click(); });
  file.addEventListener('change', function(){
    var f = file.files && file.files[0]; if (!f) return;
    note.textContent = ''; save.disabled = true; data = null;
    var reader = new FileReader();
    reader.onload = function(){
      var img = new Image();
      img.onload = function(){
        // Centre crop to a square and shrink to 256px so the upload stays small
        var s = Math.min(img.width, img.height), c = document.createElement('canvas');
        c.width = c.height = 256;
        var ctx = c.getContext('2d');
        ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, 256, 256);
        ctx.drawImage(img, (img.width - s) / 2, (img.height - s) / 2, s, s, 0, 0, 256, 256);
        data = c.toDataURL('image/jpeg', 0.85);
        pv.innerHTML = '<img class="av" style="width:120px;height:120px" src="' + data + '" alt="">';
        save.disabled = false;
      };
      img.onerror = function(){ note.textContent = 'Could not read that picture. Try a JPG or PNG.'; };
      img.src = reader.result;
    };
    reader.readAsDataURL(f);
  });
  save.addEventListener('click', function(){
    if (!data) return;
    save.disabled = true; note.textContent = 'Saving...';
    post('/api/avatar', {image: data}).then(function(x){
      if (x.ok) location.reload(); else { note.textContent = x.j.error || 'Could not save the picture.'; save.disabled = false; }
    }).catch(function(){ note.textContent = 'Could not save. Check your connection.'; save.disabled = false; });
  });
  if (remove) remove.addEventListener('click', function(){
    post('/api/avatar/remove').then(function(x){ if (x.ok) location.reload(); else note.textContent = x.j.error || 'Could not remove it.'; });
  });
})();
"""


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
  var offset = 0, seen = null, lastJson = '', soundOn = true, flashTimer = null;
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
      '<div class="a"><b>' + esc(s.asset) + '</b><small>' + esc(s.expiry_mins) + ' min trade</small></div>' +
      '<div class="d ' + dir + '">' + arrow + ' ' + esc(s.action) + '</div><div>' + resultChip(s) + '</div></div>';
  }
  function statBox(st){
    var dec = st.wins + st.losses, rate = dec ? Math.round(st.wins * 100 / dec) + '%' : '-';
    return '<div class="statbox"><small>Last 7 days</small><div class="num">' + rate +
      '<span>' + st.wins + 'W &middot; ' + st.losses + 'L &middot; ' + st.draws + 'D</span></div></div>';
  }

  function render(d){
    ['patience', '3min'].forEach(function(m){
      var mine = d.signals.filter(function(s){ return s.market === m; });
      var open = mine.filter(function(s){ return s.status === 'active'; });
      document.getElementById('live-' + m).innerHTML = open.length ? open.map(liveCard).join('') :
        '<div class="waiting"><div class="radar"></div><b style="color:var(--text)">Waiting for the next signal</b><br>' + esc(BOT[m]) + ' is scanning the market.</div>';
      document.getElementById('feed-' + m).innerHTML = mine.length ? mine.map(row).join('') : '<div class="empty">No results yet.</div>';
      document.getElementById('stats-' + m).innerHTML = statBox(d.stats[m]);
    });
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
      if (j !== lastJson){ lastJson = j; render(d); }
      document.getElementById('conn').textContent = 'Live';
    }).catch(function(){ document.getElementById('conn').textContent = 'Reconnecting...'; });
  }
  document.getElementById('alerts').addEventListener('click', function(){
    soundOn = !soundOn; this.textContent = soundOn ? 'Sound on' : 'Sound off';
    if (soundOn) beep();
    try{ if (window.Notification && Notification.permission === 'default') Notification.requestPermission(); }catch(e){}
  });
  setInterval(tick, 1000); setInterval(poll, 4000); poll();
})();
"""


CHAT_JS = r"""
(function(){
  var box = document.getElementById('chat-box'), form = document.getElementById('chat-form'),
      input = document.getElementById('chat-input'), note = document.getElementById('chat-note'),
      sendBtn = document.getElementById('chat-send'), isAdminView = !!window.CHAT_ADMIN;
  var lastSig = '', timeFmt = new Intl.DateTimeFormat('en-US', {hour:'numeric', minute:'2-digit', hour12:true, timeZone:'Africa/Lagos'});
  function esc(s){ return String(s).replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
  function render(d){
    var sig = d.messages.map(function(m){ return m.id + ':' + (m.av || 0); }).join(',') + '|' + d.muted;
    if (sig === lastSig) return;
    var firstLoad = lastSig === '';
    var nearBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 90;
    lastSig = sig;
    if (!d.messages.length){
      box.innerHTML = '<div class="chat-empty">No messages yet. Say hello to the other members.</div>';
    } else {
      box.innerHTML = d.messages.map(function(m){
        var del = isAdminView ? '<button class="chat-del" data-id="' + m.id + '" title="Delete message" type="button">&times;</button>' : '';
        var badge = m.is_admin ? '<span class="chat-badge">Admin</span>' : '';
        var pic = m.is_admin ? '' : window.dhAvatar({id: m.user_id, username: m.username, av: m.av}, 22);
        var who = (m.is_admin || m.mine || isAdminView || !m.user_id)
          ? pic + '<b>' + esc(m.username) + '</b>'
          : '<button class="chat-who" type="button" data-uid="' + m.user_id + '" title="Message ' + esc(m.username) + '">' + pic + '<b>' + esc(m.username) + '</b></button>';
        return '<div class="chat-row' + (m.mine ? ' mine' : '') + '"><div class="chat-bubble' + (m.is_admin ? ' admin' : '') + '">' +
          '<div class="chat-meta">' + who + badge + '<span>' + timeFmt.format(new Date(m.at)) + '</span>' + del + '</div>' +
          '<div class="chat-text">' + esc(m.text) + '</div></div></div>';
      }).join('');
    }
    if (firstLoad || nearBottom) box.scrollTop = box.scrollHeight;
    if (d.muted){ input.disabled = true; sendBtn.disabled = true; input.placeholder = 'You have been muted by the admin'; }
    else { input.disabled = false; sendBtn.disabled = false; input.placeholder = 'Message everyone...'; }
  }
  function poll(){
    fetch('/api/chat', {credentials:'same-origin', cache:'no-store'}).then(function(r){
      if (r.status === 401){ location.href = '/login'; return null; }
      if (r.status === 403){ return null; }
      return r.json();
    }).then(function(d){ if (d) render(d); }).catch(function(){});
  }
  form.addEventListener('submit', function(ev){
    ev.preventDefault();
    var text = input.value.trim(); if (!text) return;
    sendBtn.disabled = true; note.textContent = '';
    fetch('/api/chat', {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body: JSON.stringify({text: text})})
      .then(function(r){ return r.json().then(function(j){ return {ok:r.ok, j:j}; }); })
      .then(function(x){
        if (x.ok){ input.value = ''; lastSig = ''; poll(); }
        else { note.textContent = x.j.error || 'Could not send.'; }
        sendBtn.disabled = false; input.focus();
      }).catch(function(){ note.textContent = 'Could not send. Check your connection.'; sendBtn.disabled = false; });
  });
  box.addEventListener('click', function(ev){
    var w = ev.target.closest('.chat-who');
    if (w){ var uid = parseInt(w.dataset.uid, 10);
      if (window.dhOpenDM) window.dhOpenDM(uid); else location.href = '/app/messages?u=' + uid; return; }
    var b = ev.target.closest('.chat-del'); if (!b) return;
    fetch('/admin/chat/' + b.dataset.id + '/delete', {method:'POST', credentials:'same-origin'}).then(function(){ lastSig = ''; poll(); });
  });
  setInterval(poll, 4000); poll();
})();
"""


def chat_card(admin: bool = False) -> str:
    sub = ("Members can see and answer you here. Tap &times; to delete a message." if admin
           else "Chat with other members and the admin. Be respectful. Links are not allowed.")
    return f"""
  <section class="botcol chat-card" id="chat">
    <div class="colhead"><h2>Community chat</h2><span class="tag g" style="margin:0">Members</span></div>
    <p class="chat-sub">{sub}</p>
    <div class="chat-box" id="chat-box"><div class="chat-empty">Loading chat...</div></div>
    <div class="chat-note" id="chat-note"></div>
    <form class="chat-form" id="chat-form" autocomplete="off">
      <input id="chat-input" type="text" maxlength="400" placeholder="Message everyone..." autocomplete="off">
      <button id="chat-send" class="btn btn-primary btn-sm" type="submit">Send</button>
    </form>
  </section>
  <script>window.CHAT_ADMIN = {"true" if admin else "false"};</script>
  <script>{AVATAR_JS}</script>
  <script>{CHAT_JS}</script>"""


DM_JS = r"""
(function(){
  var el = function(id){ return document.getElementById(id); };
  var listView = el('dm-list-view'), threadView = el('dm-thread-view'), threadsEl = el('dm-threads'),
      resultsEl = el('dm-results'), search = el('dm-search'), who = el('dm-who'), box = el('dm-box'),
      form = el('dm-form'), input = el('dm-input'), note = el('dm-note'), sendBtn = el('dm-send');
  var esc = window.dhEsc, av = window.dhAvatar, current = null, sigThreads = '', sigMsgs = '', timer = null;
  var timeFmt = new Intl.DateTimeFormat('en-US', {hour:'numeric', minute:'2-digit', hour12:true, timeZone:'Africa/Lagos'});
  function api(url, opts){
    opts = opts || {}; opts.credentials = 'same-origin'; opts.cache = 'no-store';
    return fetch(url, opts).then(function(r){
      if (r.status === 401){ location.href = '/login'; return null; }
      return r.json().then(function(j){ return {ok:r.ok, status:r.status, j:j}; });
    }).catch(function(){ return null; });
  }
  function setBadge(n){
    ['dm-badge', 'dm-badge-top'].forEach(function(id){
      var b = el(id); if (!b) return;
      if (n > 0){ b.textContent = n > 99 ? '99+' : n; b.hidden = false; } else { b.hidden = true; }
    });
  }
  function item(u, right, sub){
    return '<button type="button" class="dm-item" data-uid="' + u.id + '">' + av(u, 40) +
      '<span class="dm-mid"><b>' + esc(u.username) + '</b>' + (sub ? '<span class="dm-last">' + esc(sub) + '</span>' : '') + '</span>' + (right || '') + '</button>';
  }
  function loadThreads(){
    api('/api/dm/threads').then(function(x){
      if (!x || !x.ok) return;
      setBadge(x.j.unread);
      var sig = JSON.stringify(x.j.threads.map(function(t){ return [t.id, t.av, t.last, t.unread, t.at]; }));
      if (sig === sigThreads) return;
      sigThreads = sig;
      if (!x.j.threads.length){ threadsEl.innerHTML = '<div class="chat-empty">No conversations yet. Search for a member above and say hello.</div>'; return; }
      threadsEl.innerHTML = x.j.threads.map(function(t){
        var right = t.unread ? '<span class="dm-badge">' + t.unread + '</span>' : '<span class="dm-time">' + timeFmt.format(new Date(t.at)) + '</span>';
        return item(t, right, (t.mine ? 'You: ' : '') + t.last);
      }).join('');
    });
  }
  function doSearch(){
    api('/api/dm/users?q=' + encodeURIComponent(search.value.trim())).then(function(x){
      if (!x || !x.ok) return;
      resultsEl.innerHTML = x.j.users.length ? x.j.users.map(function(u){ return item(u, '', ''); }).join('')
        : '<div class="chat-empty">No members found.</div>';
    });
  }
  search.addEventListener('input', function(){
    clearTimeout(timer);
    if (!search.value.trim()){ resultsEl.innerHTML = ''; return; }
    timer = setTimeout(doSearch, 250);
  });
  search.addEventListener('focus', function(){ if (!search.value.trim()) doSearch(); });

  function renderThread(d, first){
    who.innerHTML = av(d.other, 32) + '<b>' + esc(d.other.username) + '</b>';
    var sig = d.messages.map(function(m){ return m.id; }).join(',') + '|' + d.muted;
    if (sig === sigMsgs) return;
    sigMsgs = sig;
    var near = box.scrollHeight - box.scrollTop - box.clientHeight < 90;
    box.innerHTML = d.messages.length ? d.messages.map(function(m){
      return '<div class="chat-row' + (m.mine ? ' mine' : '') + '"><div class="chat-bubble"><div class="chat-meta"><span>' +
        timeFmt.format(new Date(m.at)) + '</span></div><div class="chat-text">' + esc(m.text) + '</div></div></div>';
    }).join('') : '<div class="chat-empty">No messages yet. Say hello.</div>';
    if (first || near) box.scrollTop = box.scrollHeight;
    input.disabled = sendBtn.disabled = !!d.muted;
    if (d.muted) input.placeholder = 'You have been muted by the admin';
  }
  function loadThread(first){
    if (current === null) return;
    var id = current;
    api('/api/dm/' + id).then(function(x){
      if (!x || id !== current) return;
      if (!x.ok){ note.textContent = x.j.error || 'Could not load this chat.'; if (x.status === 404) closeThread(); return; }
      renderThread(x.j, first);
    });
  }
  function openDM(id){
    if (!id) return;
    current = id; sigMsgs = '';
    listView.hidden = true; threadView.hidden = false;
    who.innerHTML = ''; note.textContent = ''; input.value = '';
    box.innerHTML = '<div class="chat-empty">Loading...</div>';
    search.value = ''; resultsEl.innerHTML = '';
    el('dm').scrollIntoView({behavior:'smooth', block:'start'});
    loadThread(true);
  }
  function closeThread(){
    current = null; threadView.hidden = true; listView.hidden = false; sigThreads = ''; loadThreads();
  }
  el('dm-back').addEventListener('click', closeThread);
  el('dm').addEventListener('click', function(ev){
    var b = ev.target.closest('.dm-item'); if (b) openDM(parseInt(b.dataset.uid, 10));
  });
  form.addEventListener('submit', function(ev){
    ev.preventDefault();
    var text = input.value.trim(); if (!text || current === null) return;
    sendBtn.disabled = true; note.textContent = '';
    api('/api/dm/' + current, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({text: text})}).then(function(x){
      if (x && x.ok){ input.value = ''; sigMsgs = ''; loadThread(true); }
      else { note.textContent = (x && x.j && x.j.error) || 'Could not send. Check your connection.'; }
      sendBtn.disabled = false; input.focus();
    });
  });
  window.dhOpenDM = openDM;
  var want = new URLSearchParams(location.search).get('u');
  if (want && /^[0-9]+$/.test(want)){ openDM(parseInt(want, 10)); history.replaceState(null, '', location.pathname); }
  setInterval(function(){ if (current !== null) loadThread(false); }, 3000);
  setInterval(loadThreads, 8000);
  loadThreads();
})();
"""


def dm_card() -> str:
    return f"""
  <section class="botcol dm-card" id="dm">
    <div class="colhead"><h2>Private messages <span id="dm-badge" class="dm-badge" hidden></span></h2><span class="tag b" style="margin:0">1 to 1</span></div>
    <div id="dm-list-view">
      <p class="chat-sub">Message another member privately. Only the two of you can see these. Links are not allowed.</p>
      <input id="dm-search" class="dm-search" type="text" maxlength="20" placeholder="Find a member by username..." autocomplete="off">
      <div id="dm-results"></div>
      <div class="sec-title">Conversations</div>
      <div id="dm-threads"><div class="chat-empty">Loading...</div></div>
    </div>
    <div id="dm-thread-view" hidden>
      <div class="dm-top"><button id="dm-back" class="btn btn-ghost btn-sm" type="button">&larr; Back</button><div id="dm-who"></div></div>
      <div class="chat-box" id="dm-box"></div>
      <div class="chat-note" id="dm-note"></div>
      <form class="chat-form" id="dm-form" autocomplete="off">
        <input id="dm-input" type="text" maxlength="400" placeholder="Write a message..." autocomplete="off">
        <button id="dm-send" class="btn btn-primary btn-sm" type="submit">Send</button>
      </form>
    </div>
  </section>
  <script>{DM_JS}</script>"""


HUB_CSS = """<style>
.hub-hello{display:flex;align-items:center;gap:14px;margin-bottom:24px}
.hub-hello h1{font-size:1.5rem;letter-spacing:-.5px;line-height:1.2}
.hub-hello p{color:var(--muted);font-size:.92rem}
.hub-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}
@media(max-width:700px){.hub-grid{grid-template-columns:1fr}}
.tile{display:flex;align-items:center;gap:16px;background:var(--card);border:1px solid var(--line);border-radius:20px;padding:20px;
  transition:transform .15s,border-color .15s,background .15s}
.tile:hover{transform:translateY(-2px);border-color:rgba(79,140,255,.5);background:var(--card2)}
.tile-ic{width:54px;height:54px;border-radius:16px;display:grid;place-items:center;flex:none;color:var(--blue);background:rgba(79,140,255,.14)}
.tile-ic.g{color:var(--green);background:rgba(25,211,162,.13)}
.tile-ic.a{color:var(--amber);background:rgba(251,191,36,.13)}
.tile-ic.p{color:#a78bfa;background:rgba(167,139,250,.14)}
.tile h3{font-size:1.08rem;margin:0 0 3px;display:flex;align-items:center;gap:8px}
.tile p{color:var(--muted);font-size:.88rem;margin:0}
.tile .go{margin-left:auto;color:var(--muted);flex:none}
.live-pill{display:inline-flex;align-items:center;gap:6px;font-size:.68rem;font-weight:800;letter-spacing:.8px;text-transform:uppercase;
  color:var(--green);background:rgba(25,211,162,.13);padding:2px 9px;border-radius:999px}
.live-pill::before{content:"";width:7px;height:7px;border-radius:50%;background:var(--green);animation:blink 1.4s infinite}
.live-pill[hidden]{display:none}
@keyframes blink{50%{opacity:.25}}
@media (prefers-reduced-motion:reduce){.live-pill::before{animation:none}}
.page{max-width:760px;margin:0 auto}
.page .chat-box{height:min(64vh,560px)}
.back{display:inline-flex;align-items:center;gap:6px}
</style>"""

_ICON = {
    "signals": '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>',
    "chat": '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    "dm": '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>',
    "profile": '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
}
_CHEV = '<svg class="go" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>'

HUB_JS = r"""
(function(){
  function api(u){ return fetch(u, {credentials:'same-origin', cache:'no-store'}).then(function(r){
    if (r.status === 401){ location.href = '/login'; return null; } return r.ok ? r.json() : null; }).catch(function(){ return null; }); }
  function refresh(){
    if (document.hidden) return;
    api('/api/signals').then(function(d){
      var el = document.getElementById('live-count'); if (!d || !el) return;
      var n = d.signals.filter(function(s){ return s.status === 'active'; }).length;
      el.hidden = !n; el.textContent = n + ' live';
    });
    var b = document.getElementById('dm-badge');
    if (b) api('/api/dm/threads').then(function(d){
      if (!d) return; b.hidden = !(d.unread > 0); b.textContent = d.unread > 99 ? '99+' : d.unread;
    });
  }
  refresh(); setInterval(refresh, 15000);
})();
"""


def _logout_form() -> str:
    return ('<form method="post" action="/logout" style="display:inline">'
            '<button class="linkbtn" type="submit">Log out</button></form>')


def _home_link() -> str:
    return '<a class="btn btn-ghost btn-sm back" href="/app">&larr; Home</a>'


def user_hub(email: str, chat_name: str = "", me: dict = None) -> str:
    """The page members land on after login: a menu that opens each area as its own page."""
    def tile(href, icon, tint, title, text, extra=""):
        return (f'<a class="tile" href="{href}"><span class="tile-ic {tint}">{_ICON[icon]}</span>'
                f'<div><h3>{title}{extra}</h3><p>{text}</p></div>{_CHEV}</a>')
    tiles = [
        tile("/app/signals", "signals", "g", "Trades &amp; signals",
             "Live signals from the Patience Bot and the 3 min Bot, with entry times and results.",
             ' <span class="live-pill" id="live-count" hidden></span>'),
        tile("/app/chat", "chat", "", "Community chat", "Talk with other members and the admin."),
    ]
    if me:
        tiles.append(tile("/app/messages", "dm", "p", "Private messages", "One to one chats with other members.",
                          ' <span id="dm-badge" class="dm-badge" hidden></span>'))
        tiles.append(tile("/app/settings", "profile", "a", "Profile", "Your picture and account details."))
    name = esc(chat_name or email)
    hello = (avatar_html(me, 48) if me else "")
    body = f"""
{topbar(_logout_form())}
<main class="dash"><div class="wrap"><div class="page">
  <div class="hub-hello">{hello}<div><h1>Welcome, {name}</h1><p>Choose where you want to go.</p></div></div>
  <div class="hub-grid">{"".join(tiles)}</div>
  <p class="fine">{esc(RISK_TEXT)}</p>
</div></div></main>
<script>{HUB_JS}</script>
</body></html>"""
    return head(f"Home | {SITE}", HUB_CSS) + "<body>" + body


def user_dashboard(email: str, chat_name: str = "", me: dict = None) -> str:
    """Trades and signals page (the bots)."""
    body = f"""
{topbar(_logout_form())}
<main class="dash"><div class="wrap">
  <div class="dash-head">
    <div><h1>Live signals</h1><p>{avatar_html(me, 22) + " " if me else ""}Signed in as {esc(chat_name or email)} &middot; <span id="conn">Connecting...</span></p></div>
    <div class="tools">{_home_link()}<button id="alerts" class="btn btn-ghost btn-sm" type="button">Sound on</button></div>
  </div>
  <div class="botgrid">
    <section class="botcol">
      <div class="colhead"><h2>Patience Bot</h2><span class="tag g" style="margin:0">Patience Bot</span></div>
      <div id="stats-patience"></div>
      <div class="sec-title">Live now</div>
      <div id="live-patience"></div>
      <div class="sec-title">Recent results</div>
      <div class="feed" id="feed-patience"><div class="empty">Loading...</div></div>
    </section>
    <section class="botcol">
      <div class="colhead"><h2>3 min Bot</h2><span class="tag b" style="margin:0">3 min Bot</span></div>
      <div id="stats-3min"></div>
      <div class="sec-title">Live now</div>
      <div id="live-3min"></div>
      <div class="sec-title">Recent results</div>
      <div class="feed" id="feed-3min"><div class="empty">Loading...</div></div>
    </section>
  </div>
  <p class="fine">Times are shown in WAT. Place the trade at the entry time. {esc(RISK_TEXT)}</p>
</div></main>
<script>{DASH_JS}</script>
</body></html>"""
    return head(f"Signals | {SITE}") + "<body>" + body


def chat_page(chat_name: str = "") -> str:
    body = f"""
{topbar(_logout_form())}
<main class="dash"><div class="wrap"><div class="page">
  <div class="dash-head"><div><h1>Community chat</h1><p>Signed in as {esc(chat_name)}</p></div>
    <div class="tools">{_home_link()}</div></div>
  {chat_card(False)}
</div></div></main>
</body></html>"""
    return head(f"Community chat | {SITE}", HUB_CSS) + "<body>" + body


def messages_page(chat_name: str = "") -> str:
    body = f"""
{topbar(_logout_form())}
<main class="dash"><div class="wrap"><div class="page">
  <div class="dash-head"><div><h1>Private messages</h1><p>Signed in as {esc(chat_name)}</p></div>
    <div class="tools">{_home_link()}</div></div>
  <script>{AVATAR_JS}</script>
  {dm_card()}
</div></div></main>
</body></html>"""
    return head(f"Private messages | {SITE}", HUB_CSS) + "<body>" + body


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
    right = ('<a class="btn btn-sm" href="/admin/pairs">Pairs record</a>'
             '<a class="btn btn-ghost btn-sm" href="/app">User view</a>'
             '<form method="post" action="/logout" style="display:inline"><button class="linkbtn" type="submit">Log out</button></form>')
    def bot_card(path, name, key):
        info = esc(bot_info.get(key, ""))
        return (f'<a class="card hub-card" href="{path}"><h3>{name} controls</h3>'
                f'<p>Monitor performance, control scanning, and skip published signals.</p><p style="margin-top:10px;font-size:.82rem">{info}</p></a>')
    approval = "Approval required for new accounts" if require_approval else "New accounts get access straight away"
    body = f"""
{topbar(right)}
<main class="dash"><div class="wrap">
  <div class="dash-head"><div><h1>Admin</h1><p>{esc(approval)}</p></div></div>
  <div class="grid3">
    {bot_card("/admin/patience", "Patience Bot", "patience")}
    {bot_card("/admin/3min", "3 min Bot", "3min")}
    <a class="card hub-card" href="/admin/chat"><h3>Community chat</h3>
      <p>Read and reply to members, delete messages.</p></a>
    <a class="card hub-card" href="/admin/users"><h3>Members</h3>
      <p>{user_count} account(s){f", {waiting} waiting for approval" if waiting else ""}</p>
      <p style="margin-top:10px;font-size:.82rem">Enable or disable access.</p></a>
  </div>
  <p class="fine"><a href="/status" style="text-decoration:underline">Price data and bot status (JSON)</a></p>
</div></main></body></html>"""
    return head(f"Admin | {SITE}") + "<body>" + body


def admin_pairs_page(rows: list, market: str, period: str, min_trades: int) -> str:
    right = ('<a class="btn btn-ghost btn-sm" href="/admin">Back</a>')
    def tabs(param, options, current):
        out = ""
        for key, label in options:
            q = {"market": market, "period": period}
            q[param] = key
            cls = "tab on" if key == current else "tab"
            out += f'<a class="{cls}" href="/admin/pairs?market={q["market"]}&amp;period={q["period"]}">{label}</a>'
        return f'<div class="tabs">{out}</div>'
    market_tabs = tabs("market", [("all", "All bots"), ("patience", "Patience Bot"), ("3min", "3 min Bot")], market)
    period_tabs = tabs("period", [("all", "All time"), ("30", "Last 30 days"), ("7", "Last 7 days"), ("1", "Today")], period)

    body_rows = ""
    for r in rows:
        trades = r["wins"] + r["losses"]
        rate = "-" if r["rate"] is None else f'{r["rate"]}%'
        color = "var(--muted)" if r["rate"] is None else ("var(--green)" if r["rate"] >= 60 else ("var(--red)" if r["rate"] < 50 else "var(--amber)"))
        body_rows += (
            f'<tr><td><b>{esc(r["pair"])}</b></td>'
            f'<td style="font-weight:800;font-size:1.1rem">{trades}</td>'
            f'<td style="color:var(--green);font-weight:800;font-size:1.1rem">{r["wins"]}</td>'
            f'<td style="color:var(--red);font-weight:800;font-size:1.1rem">{r["losses"]}</td>'
            f'<td><b style="color:{color}">{rate}</b></td></tr>'
        )
    if not body_rows:
        body_rows = '<tr><td colspan="5" class="empty">No results recorded yet. Log WIN or LOSS on trades and they will show here.</td></tr>'
    wins = sum(r["wins"] for r in rows)
    losses = sum(r["losses"] for r in rows)
    decided = wins + losses
    overall = f"{round(wins * 100 / decided)}%" if decided else "-"
    body = f"""
{topbar(right)}
<main class="dash"><div class="wrap">
  <div class="dash-head"><div><h1>Pairs record</h1>
    <p>Number of trades, wins and losses for each pair.</p></div></div>
  {market_tabs}{period_tabs}
  <div class="statbox" style="margin-bottom:18px"><small>All pairs</small><div class="num">{decided} trades<span>{wins} wins &middot; {losses} losses &middot; {overall}</span></div></div>
  <div class="card scroll"><table class="table"><thead><tr><th>Pair</th><th>Trades</th><th>Wins</th><th>Losses</th><th>Win rate</th></tr></thead>
  <tbody>{body_rows}</tbody></table></div>
  <p class="fine">Trades = wins + losses. Draws, skipped and expired signals are not counted.</p>
</div></main></body></html>"""
    return head(f"Pairs record | {SITE}") + "<body>" + body


def admin_chat_page() -> str:
    right = '<a class="btn btn-ghost btn-sm" href="/admin">Back</a>'
    body = f"""
{topbar(right)}
<main class="dash"><div class="wrap">
  <div class="dash-head"><div><h1>Community chat</h1><p>You post as Admin, with a badge members can see.</p></div></div>
  {chat_card(True)}
</div></main></body></html>"""
    return head(f"Chat | {SITE}") + "<body>" + body


def admin_users_page(users: list, require_approval: bool, message: str = "") -> str:
    right = '<a class="btn btn-ghost btn-sm" href="/admin">Back</a>'
    rows = ""
    for u in users:
        active = bool(u["is_active"])
        chip = '<span class="chip win">Active</span>' if active else '<span class="chip wait">Disabled</span>'
        if u.get("is_muted"):
            chip += ' <span class="chip loss">Muted</span>'
        btn = (f'<button class="btn btn-sm btn-danger" type="submit">Disable</button>' if active
               else f'<button class="btn btn-sm btn-ok" type="submit">Enable</button>')
        mute = (f'<button class="btn btn-sm btn-ok" type="submit">Unmute</button>' if u.get("is_muted")
                else f'<button class="btn btn-sm btn-ghost" type="submit">Mute chat</button>')
        name = esc(u.get("full_name") or "-")
        handle = f'@{esc(u["username"])}' if u.get("username") else "-"
        rows += (f'<tr><td>{name}<br><small style="color:var(--muted)">{handle}</small></td><td>{esc(u["email"])}</td>'
                 f'<td>{esc(u["joined"])}</td><td>{chip}</td>'
                 f'<td><div style="display:flex;gap:6px;flex-wrap:wrap">'
                 f'<form method="post" action="/admin/users/{int(u["id"])}/toggle">{btn}</form>'
                 f'<form method="post" action="/admin/users/{int(u["id"])}/mute">{mute}</form></div></td></tr>')
    if not rows:
        rows = '<tr><td colspan="5" class="empty">No members yet.</td></tr>'
    note = ("New accounts start disabled. Enable them once payment is confirmed." if require_approval
            else "New accounts are active straight away. Set REQUIRE_APPROVAL=1 in Render to approve each one yourself.")
    msg = f'<div class="msg ok">{esc(message)}</div>' if message else ""
    body = f"""
{topbar(right)}
<main class="dash"><div class="wrap">
  <div class="dash-head"><div><h1>Members</h1><p>{esc(note)}</p></div></div>{msg}
  <div class="card scroll"><table class="table"><thead><tr><th>Name</th><th>Email</th><th>Joined</th><th>Status</th><th></th></tr></thead>
  <tbody>{rows}</tbody></table></div>
</div></main></body></html>"""
    return head(f"Members | {SITE}") + "<body>" + body
