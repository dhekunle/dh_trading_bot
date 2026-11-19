"""Shared styling and the logo for every DH Binary Trader page."""

SITE = "DH Binary Trader"

LOGO_MARK = (
    '<svg viewBox="0 0 40 40" width="34" height="34" aria-hidden="true">'
    '<defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#19d3a2"/><stop offset="1" stop-color="#4f8cff"/></linearGradient></defs>'
    '<rect width="40" height="40" rx="11" fill="url(#lg)"/>'
    '<path d="M9 27 L16 18 L21 23 L31 11" fill="none" stroke="#06121c" stroke-width="3.2" '
    'stroke-linecap="round" stroke-linejoin="round"/>'
    '<circle cx="31" cy="11" r="2.6" fill="#06121c"/></svg>'
)

CSS = r"""
:root{
  --bg:#070a12; --bg2:#0c1222; --card:rgba(255,255,255,.045); --card2:rgba(255,255,255,.075);
  --line:rgba(255,255,255,.09); --text:#e9eef7; --muted:#8d98ad;
  --green:#19d3a2; --red:#ff5d73; --amber:#fbbf24; --blue:#4f8cff;
  --grad:linear-gradient(135deg,#19d3a2 0%,#4f8cff 100%);
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{
  font-family:Inter,system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  color:var(--text);line-height:1.55;min-height:100vh;-webkit-font-smoothing:antialiased;
  background:
    radial-gradient(1000px 520px at 85% -8%,rgba(79,140,255,.20),transparent 60%),
    radial-gradient(800px 460px at -8% 8%,rgba(25,211,162,.15),transparent 55%),
    var(--bg);
  background-attachment:fixed;
}
a{color:inherit;text-decoration:none}
button{font-family:inherit}
.wrap{max-width:1120px;margin:0 auto;padding:0 20px}

/* top bar */
.topbar{position:sticky;top:0;z-index:30;background:rgba(7,10,18,.72);
  backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);border-bottom:1px solid var(--line)}
.topbar .wrap{display:flex;align-items:center;justify-content:space-between;height:64px;gap:14px}
.logo{display:flex;align-items:center;gap:10px;font-weight:800;letter-spacing:-.2px;font-size:1.05rem}
.logo small{display:block;font-weight:600;font-size:.62rem;letter-spacing:2px;color:var(--muted);text-transform:uppercase;margin-top:-2px}
.navlinks{display:flex;align-items:center;gap:6px}
.navlinks a.link{color:var(--muted);font-size:.92rem;padding:8px 12px;border-radius:10px}
.navlinks a.link:hover{color:var(--text);background:var(--card)}
@media(max-width:760px){.navlinks a.link{display:none}}

/* buttons */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;border:0;cursor:pointer;
  font-weight:700;font-size:.95rem;padding:11px 20px;border-radius:12px;transition:transform .15s,box-shadow .15s,background .15s}
.btn-primary{background:var(--grad);color:#04141c;box-shadow:0 8px 30px rgba(25,211,162,.25)}
.btn-primary:hover{transform:translateY(-1px);box-shadow:0 12px 36px rgba(79,140,255,.35)}
.btn-ghost{background:var(--card);color:var(--text);border:1px solid var(--line)}
.btn-ghost:hover{background:var(--card2)}
.btn-lg{padding:15px 28px;font-size:1.02rem;border-radius:14px}
.btn-sm{padding:7px 13px;font-size:.82rem;border-radius:9px}
.btn-danger{background:rgba(255,93,115,.14);color:var(--red);border:1px solid rgba(255,93,115,.3)}
.btn-ok{background:rgba(25,211,162,.14);color:var(--green);border:1px solid rgba(25,211,162,.3)}
.linkbtn{background:none;border:0;color:var(--muted);cursor:pointer;font-size:.92rem;padding:8px 12px;border-radius:10px}
.linkbtn:hover{color:var(--text);background:var(--card)}

/* hero */
.hero{padding:74px 0 54px}
.hero-grid{display:grid;grid-template-columns:1.1fr .9fr;gap:48px;align-items:center}
@media(max-width:900px){.hero-grid{grid-template-columns:1fr;gap:36px}.hero{padding-top:44px}}
.pill{display:inline-flex;align-items:center;gap:8px;font-size:.78rem;font-weight:700;letter-spacing:.4px;
  color:var(--green);background:rgba(25,211,162,.10);border:1px solid rgba(25,211,162,.28);padding:6px 13px;border-radius:999px}
.dot{width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:0 0 0 0 rgba(25,211,162,.7);animation:pulse 1.8s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(25,211,162,.65)}70%{box-shadow:0 0 0 10px rgba(25,211,162,0)}100%{box-shadow:0 0 0 0 rgba(25,211,162,0)}}
h1.hero-title{font-size:clamp(2.2rem,5.2vw,3.7rem);line-height:1.06;letter-spacing:-1.4px;margin:18px 0 18px;font-weight:850}
.grad-text{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.lead{color:var(--muted);font-size:1.12rem;max-width:560px}
.cta-row{display:flex;flex-wrap:wrap;gap:12px;margin-top:28px}
.trust{display:flex;flex-wrap:wrap;gap:10px 22px;margin-top:30px;color:var(--muted);font-size:.86rem}
.trust span::before{content:"✓";color:var(--green);font-weight:800;margin-right:7px}

/* sample signal card */
.mock{position:relative;border-radius:22px;padding:22px;background:linear-gradient(160deg,rgba(255,255,255,.08),rgba(255,255,255,.025));
  border:1px solid var(--line);box-shadow:0 30px 80px rgba(0,0,0,.45)}
.mock::before{content:"";position:absolute;inset:-1px;border-radius:22px;padding:1px;background:var(--grad);opacity:.35;
  -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude;pointer-events:none}
.mock-tag{position:absolute;top:-12px;right:18px;background:var(--bg2);border:1px solid var(--line);color:var(--muted);
  font-size:.7rem;font-weight:700;letter-spacing:1px;text-transform:uppercase;padding:4px 11px;border-radius:999px}
.sig-head{display:flex;justify-content:space-between;align-items:center;color:var(--muted);font-size:.82rem}
.sig-main{display:flex;justify-content:space-between;align-items:center;margin:16px 0 18px}
.asset{font-size:1.9rem;font-weight:850;letter-spacing:-.6px}
.dir{font-weight:850;font-size:1.05rem;padding:9px 16px;border-radius:12px;letter-spacing:.5px}
.dir.buy{color:var(--green);background:rgba(25,211,162,.13);border:1px solid rgba(25,211,162,.35)}
.dir.sell{color:var(--red);background:rgba(255,93,115,.13);border:1px solid rgba(255,93,115,.35)}
.sig-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.sig-grid div{background:rgba(0,0,0,.25);border:1px solid var(--line);border-radius:12px;padding:11px 12px}
.sig-grid small{display:block;color:var(--muted);font-size:.7rem;letter-spacing:.8px;text-transform:uppercase}
.sig-grid b{font-size:1rem}
.sig-foot{margin-top:14px;color:var(--muted);font-size:.8rem;border-top:1px dashed var(--line);padding-top:12px}

/* sections */
.section{padding:70px 0}
.section h2{font-size:clamp(1.6rem,3.2vw,2.3rem);letter-spacing:-.8px;font-weight:800;margin-bottom:10px}
.section .sub{color:var(--muted);max-width:620px;margin-bottom:36px}
.eyebrow{color:var(--green);font-weight:800;font-size:.78rem;letter-spacing:2px;text-transform:uppercase;margin-bottom:10px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.grid2{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}
@media(max-width:860px){.grid3,.grid2{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:24px}
.card h3{font-size:1.1rem;margin-bottom:8px;letter-spacing:-.2px}
.card p{color:var(--muted);font-size:.95rem}
.step-n{width:38px;height:38px;border-radius:11px;background:var(--grad);color:#04141c;font-weight:900;
  display:flex;align-items:center;justify-content:center;margin-bottom:14px}
.bot-card{position:relative;overflow:hidden}
.bot-card .tag{display:inline-block;font-size:.7rem;font-weight:800;letter-spacing:1.2px;text-transform:uppercase;
  padding:4px 10px;border-radius:999px;margin-bottom:12px}
.tag.g{color:var(--green);background:rgba(25,211,162,.12)} .tag.b{color:var(--blue);background:rgba(79,140,255,.14)}
.ticks{list-style:none;margin-top:14px}
.ticks li{color:var(--muted);font-size:.93rem;padding:5px 0 5px 26px;position:relative}
.ticks li::before{content:"✓";position:absolute;left:0;color:var(--green);font-weight:800}
.strip{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
@media(max-width:760px){.strip{grid-template-columns:repeat(2,1fr)}}
.strip .card{text-align:center;padding:20px 12px}
.strip b{display:block;font-size:1.8rem;letter-spacing:-.8px}
.strip span{color:var(--muted);font-size:.82rem}
.cta-band{border-radius:24px;padding:46px 28px;text-align:center;border:1px solid var(--line);
  background:radial-gradient(600px 240px at 50% 0%,rgba(79,140,255,.22),transparent 70%),var(--card)}
.cta-band h2{margin-bottom:10px}
footer.site{border-top:1px solid var(--line);padding:34px 0 44px;color:var(--muted);font-size:.82rem;margin-top:30px}
footer.site p{max-width:820px;margin-top:10px}

/* auth */
.auth-wrap{min-height:calc(100vh - 64px);display:flex;align-items:center;justify-content:center;padding:32px 16px}
.auth-card{width:100%;max-width:430px;background:var(--card);border:1px solid var(--line);border-radius:22px;padding:34px 28px;
  box-shadow:0 30px 80px rgba(0,0,0,.4)}
.auth-card h1{font-size:1.6rem;letter-spacing:-.6px;margin-bottom:6px}
.auth-card .sub{color:var(--muted);margin-bottom:22px;font-size:.95rem}
label{display:block;font-size:.8rem;font-weight:700;color:var(--muted);margin:14px 0 6px;letter-spacing:.3px}
input[type=email],input[type=password],input[type=text]{width:100%;background:rgba(0,0,0,.28);border:1px solid var(--line);
  color:var(--text);padding:13px 14px;border-radius:12px;font-size:1rem;outline:none;transition:border .15s,box-shadow .15s}
input:focus{border-color:var(--blue);box-shadow:0 0 0 3px rgba(79,140,255,.22)}
.auth-card .btn{width:100%;margin-top:22px}
.alt{text-align:center;color:var(--muted);font-size:.9rem;margin-top:18px}
.alt a{color:var(--green);font-weight:700}
.msg{border-radius:12px;padding:11px 14px;font-size:.9rem;margin-bottom:6px}
.msg.err{background:rgba(255,93,115,.12);border:1px solid rgba(255,93,115,.32);color:#ffb3be}
.msg.ok{background:rgba(25,211,162,.12);border:1px solid rgba(25,211,162,.3);color:#9ef0d8}

/* user dashboard */
.dash{padding:26px 0 60px}
.dash-head{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px;margin-bottom:20px}
.dash-head h1{font-size:1.5rem;letter-spacing:-.5px}
.dash-head p{color:var(--muted);font-size:.9rem}
.tools{display:flex;gap:8px;flex-wrap:wrap}
.botgrid{display:grid;grid-template-columns:1fr 1fr;gap:22px;align-items:start}
@media(max-width:900px){.botgrid{grid-template-columns:1fr;gap:34px}}
.botcol{background:var(--card);border:1px solid var(--line);border-radius:22px;padding:20px}
.colhead{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:14px}
.colhead h2{font-size:1.15rem;letter-spacing:-.3px}
.botcol .sec-title{margin:18px 0 10px}
.botcol .live-card{background:rgba(0,0,0,.22)}
.statbox{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 18px}
.statbox small{color:var(--muted);font-size:.74rem;letter-spacing:1px;text-transform:uppercase;font-weight:700}
.statbox .num{font-size:1.5rem;font-weight:850;letter-spacing:-.5px;margin-top:3px}
.statbox .num span{font-size:.82rem;color:var(--muted);font-weight:600;margin-left:6px}
.sec-title{font-size:.78rem;letter-spacing:2px;text-transform:uppercase;color:var(--muted);font-weight:800;margin:26px 0 12px}
.waiting{border:1px dashed var(--line);border-radius:18px;padding:34px 20px;text-align:center;color:var(--muted)}
.waiting .radar{width:54px;height:54px;border-radius:50%;margin:0 auto 14px;border:2px solid rgba(25,211,162,.35);position:relative}
.waiting .radar::after{content:"";position:absolute;inset:-2px;border-radius:50%;border:2px solid var(--green);animation:ping 1.8s infinite}
@keyframes ping{0%{transform:scale(.6);opacity:.9}100%{transform:scale(1.5);opacity:0}}
.live-card{border-radius:20px;padding:20px;margin-bottom:14px;background:linear-gradient(160deg,rgba(255,255,255,.08),rgba(255,255,255,.025));
  border:1px solid var(--line);animation:drop .5s ease}
.live-card.buy{border-color:rgba(25,211,162,.45);box-shadow:0 0 0 1px rgba(25,211,162,.12),0 20px 60px rgba(25,211,162,.10)}
.live-card.sell{border-color:rgba(255,93,115,.45);box-shadow:0 0 0 1px rgba(255,93,115,.12),0 20px 60px rgba(255,93,115,.10)}
@keyframes drop{from{opacity:0;transform:translateY(-14px) scale(.98)}to{opacity:1;transform:none}}
.countdown{margin-top:14px;text-align:center;font-weight:850;font-size:1.25rem;padding:12px;border-radius:12px;background:rgba(0,0,0,.28);
  border:1px solid var(--line);font-variant-numeric:tabular-nums}
.mart{margin-top:12px;color:var(--muted);font-size:.82rem}
.chip{display:inline-block;font-size:.7rem;font-weight:800;letter-spacing:.8px;padding:3px 9px;border-radius:999px;text-transform:uppercase}
.chip.live{color:#04141c;background:var(--green)} .chip.win{color:var(--green);background:rgba(25,211,162,.14)}
.chip.loss{color:var(--red);background:rgba(255,93,115,.14)} .chip.draw{color:var(--amber);background:rgba(251,191,36,.14)}
.chip.wait{color:var(--amber);background:rgba(251,191,36,.14)}
.tabs{display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap}
.tab{background:var(--card);border:1px solid var(--line);color:var(--muted);padding:7px 14px;border-radius:999px;font-size:.84rem;font-weight:700;cursor:pointer}
.tab.on{color:#04141c;background:var(--grad);border-color:transparent}
.feed{display:flex;flex-direction:column;gap:8px}
.row{display:grid;grid-template-columns:78px 1fr auto auto;gap:12px;align-items:center;background:var(--card);border:1px solid var(--line);
  border-radius:14px;padding:12px 14px;font-size:.92rem}
.row .t{color:var(--muted);font-size:.8rem}
.row .a b{display:block}.row .a small{color:var(--muted)}
.row .d{font-weight:800}.row .d.buy{color:var(--green)}.row .d.sell{color:var(--red)}
@media(max-width:560px){.row{grid-template-columns:62px 1fr auto;}.row .d{display:none}}
.empty{color:var(--muted);text-align:center;padding:24px}
.fine{color:var(--muted);font-size:.76rem;margin-top:26px;max-width:760px}

/* admin */
.table{width:100%;border-collapse:collapse;font-size:.92rem}
.table th{color:var(--muted);text-align:left;font-size:.74rem;letter-spacing:1px;text-transform:uppercase;padding:10px 12px;border-bottom:1px solid var(--line)}
.table td{padding:12px;border-bottom:1px solid var(--line)}
.scroll{overflow-x:auto}
.hub-card{display:block;transition:transform .15s,border-color .15s}
.hub-card:hover{transform:translateY(-2px);border-color:rgba(79,140,255,.5)}

/* sign up hint + chat */
.hint{color:var(--muted);font-size:.78rem;margin-top:6px}
.chat-card{padding:20px}
.chat-sub{color:var(--muted);font-size:.84rem;margin:-4px 0 12px}
.chat-box{height:360px;overflow-y:auto;background:rgba(0,0,0,.22);border:1px solid var(--line);border-radius:16px;padding:12px;
  display:flex;flex-direction:column;gap:8px;scroll-behavior:smooth}
.chat-empty{margin:auto;color:var(--muted);text-align:center;font-size:.9rem;padding:20px}
.chat-row{display:flex}.chat-row.mine{justify-content:flex-end}
.chat-bubble{max-width:82%;background:var(--card2);border:1px solid var(--line);border-radius:14px 14px 14px 4px;padding:8px 12px}
.chat-row.mine .chat-bubble{background:rgba(79,140,255,.16);border-color:rgba(79,140,255,.35);border-radius:14px 14px 4px 14px}
.chat-bubble.admin{border-color:rgba(25,211,162,.5);background:rgba(25,211,162,.10)}
.chat-meta{display:flex;align-items:center;gap:8px;font-size:.74rem;color:var(--muted);margin-bottom:2px}
.chat-meta b{color:var(--text);font-size:.82rem}
.chat-badge{font-size:.62rem;font-weight:800;letter-spacing:.8px;text-transform:uppercase;color:#04141c;background:var(--grad);padding:1px 7px;border-radius:999px}
.chat-text{font-size:.93rem;word-break:break-word;white-space:pre-wrap}
.chat-del{margin-left:auto;background:none;border:0;color:var(--red);font-size:1.1rem;cursor:pointer;line-height:1;padding:0 2px}
.chat-form{display:flex;gap:8px;margin-top:10px}
.chat-form input{flex:1;min-width:0;background:rgba(0,0,0,.28);border:1px solid var(--line);color:var(--text);padding:12px 14px;border-radius:12px;font-size:1rem;outline:none}
.chat-form input:focus{border-color:var(--blue);box-shadow:0 0 0 3px rgba(79,140,255,.22)}
.chat-form input:disabled{opacity:.5}
.chat-note{color:var(--red);font-size:.8rem;min-height:1em;margin-top:8px}
"""
