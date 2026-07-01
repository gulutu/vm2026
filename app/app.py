"""VM 2026 — prediksjonsmodell. Én side med topp-navigasjon (mørkt matchday-tema)."""
import datetime as dt
import html
import re
import unicodedata

import duckdb
import pandas as pd
import streamlit as st

import common
import tournament
from poisson import predict_match
from scorers import scorer_table

st.set_page_config(page_title="VM 2026", page_icon="⚽", layout="wide")

# ───────────────────────────── stil ─────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800;900&family=Inter:wght@400;500;600;700&display=swap');

:root{
  --bg:#0b1220; --surface:#141f33; --surface2:#0f1828; --line:rgba(148,163,184,.16);
  --ink:#e9eef7; --muted:#8a97ab; --emerald:#34d399; --emerald-deep:#0e7a63;
  --gold:#f7c948; --blue:#5fa8ff;
}
html, body, [class*="css"], [class*="st-"]{ font-family:'Inter',system-ui,sans-serif; color:var(--ink); }
.block-container{ max-width:1240px; padding-top:.6rem; }
#MainMenu, header[data-testid="stHeader"]{ background:transparent; }
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"]{ display:none; }
h1,h2,h3,h4{ font-family:'Archivo',sans-serif; letter-spacing:-.01em; }

/* hero */
.hero{ text-align:center; padding:1.4rem 1rem 1.6rem; margin-bottom:.5rem; border-radius:20px;
  border:1px solid var(--line);
  background:radial-gradient(120% 150% at 50% -30%, rgba(52,211,153,.18), transparent 60%), var(--surface2); }
.hero .kick{ color:var(--emerald); font-size:.74rem; font-weight:800; letter-spacing:.22em;
  text-transform:uppercase; font-family:'Archivo',sans-serif; }
.hero h1{ font-size:3.1rem; font-weight:900; margin:.3rem 0 .25rem; letter-spacing:-.02em;
  background:linear-gradient(92deg,#fff 38%,var(--emerald)); -webkit-background-clip:text;
  background-clip:text; -webkit-text-fill-color:transparent; }
.hero .tag{ color:var(--muted); font-size:.92rem; max-width:48ch; margin:0 auto; line-height:1.5; }

/* nav pills */
.stButton > button{ border-radius:999px; font-weight:700; font-family:'Archivo',sans-serif;
  border:1px solid var(--line); background:var(--surface2); color:var(--muted);
  white-space:nowrap; font-size:.85rem; padding:.45rem .3rem; }
.stButton > button:hover{ border-color:var(--emerald); color:var(--ink); }

/* stat tiles */
.tiles{ display:grid; grid-template-columns:1fr 1fr 1.6fr; gap:.8rem; margin:.2rem 0 1.1rem; }
.tile{ background:var(--surface); border:1px solid var(--line); border-radius:16px;
  padding:1rem 1.1rem; text-align:center; }
.tile .tnum{ font-family:'Archivo',sans-serif; font-weight:900; font-size:2.6rem; line-height:1;
  color:var(--emerald); }
.tile .tlab{ color:var(--muted); font-size:.74rem; text-transform:uppercase; letter-spacing:.09em;
  margin-top:.35rem; }
.tile.kick{ text-align:center; display:flex; flex-direction:column; justify-content:center; align-items:center; }
.tile.kick .klab{ color:var(--gold); font-size:.7rem; text-transform:uppercase; letter-spacing:.1em;
  font-weight:700; }
.tile.kick .kteams{ font-family:'Archivo',sans-serif; font-weight:800; font-size:1.35rem; margin:.15rem 0; }
.tile.kick .kmeta{ color:var(--muted); font-size:.82rem; }

.section{ font-family:'Archivo',sans-serif; font-weight:800; font-size:1.3rem; margin:1.7rem 0 .35rem;
  display:flex; align-items:center; gap:.55rem; }
.section::before{ content:""; width:.5rem; height:1.4rem; border-radius:3px; flex:none;
  background:linear-gradient(var(--emerald),var(--emerald-deep)); }
.lead{ color:var(--muted); font-size:.86rem; margin-bottom:.7rem; }

/* podium */
.podium{ display:grid; grid-template-columns:repeat(3,1fr); gap:.9rem; align-items:end; }
.pod{ border-radius:18px; padding:1.3rem .8rem 1.1rem; text-align:center; position:relative;
  background:var(--surface); border:1px solid var(--line); overflow:hidden; }
.pod::before{ content:""; position:absolute; inset:0 0 auto 0; height:4px; }
.pod.g1::before{ background:var(--gold);} .pod.g2::before{ background:#cbd5e1;} .pod.g3::before{ background:#d08a52;}
.pod .rank{ font-family:'Archivo',sans-serif; font-weight:900; font-size:1.1rem; color:var(--muted); }
.pod.g1 .rank{ color:var(--gold);} .pod.g2 .rank{ color:#cbd5e1;} .pod.g3 .rank{ color:#d08a52;}
.pod .team{ font-family:'Archivo',sans-serif; font-weight:800; font-size:1.15rem; margin-top:.3rem; }
.pod .big{ font-family:'Archivo',sans-serif; font-weight:900; font-size:2.7rem; line-height:1.05;
  color:#fff; margin:.1rem 0; }
.pod.g1 .big{ color:var(--gold); }
.pod.g1{ transform:translateY(-18px); padding-top:1.7rem; padding-bottom:1.3rem; }
.pod.g1 .big{ font-size:3.1rem; }
.pod .crown{ font-size:1.3rem; margin-bottom:-.1rem; }
.pod .sub{ color:var(--muted); font-size:.7rem; text-transform:uppercase; letter-spacing:.09em; }

/* stat-rows m/ bjelke */
.rows{ background:var(--surface); border:1px solid var(--line); border-radius:16px; padding:.5rem .9rem; }
.srow{ display:grid; grid-template-columns:1.3rem 1fr auto; gap:.7rem; align-items:center;
  padding:.5rem 0; border-top:1px solid var(--line); }
.srow:first-child{ border-top:none; }
.srow .rk{ color:var(--muted); font-size:.8rem; font-variant-numeric:tabular-nums; text-align:right; }
.srow .nm{ font-weight:600; }
.srow .nm .meta{ color:var(--muted); font-weight:500; font-size:.78rem; margin-left:.4rem; }
.srow .track{ height:7px; border-radius:99px; background:rgba(148,163,184,.14); margin-top:.32rem; overflow:hidden; }
.srow .fill{ height:100%; border-radius:99px; background:linear-gradient(90deg,var(--emerald-deep),var(--emerald)); }
.srow .val{ font-family:'Archivo',sans-serif; font-weight:800; font-variant-numeric:tabular-nums; }

/* group wallchart cards */
.ggrid{ display:grid; grid-template-columns:1fr 1fr; gap:1rem; }
.gcard{ background:var(--surface); border:1px solid var(--line); border-radius:16px; padding:1rem 1.1rem; }
.gcap{ display:flex; align-items:center; justify-content:center; gap:.55rem; font-family:'Archivo',sans-serif;
  font-weight:800; font-size:1.1rem; margin-bottom:.7rem; }
.gcap .badge{ width:1.8rem; height:1.8rem; display:grid; place-items:center; border-radius:9px;
  background:var(--emerald); color:#06281f; font-weight:900; }
.trow{ display:grid; grid-template-columns:1fr 4.2rem; align-items:center; gap:.6rem; padding:.34rem 0; }
.trow + .trow{ border-top:1px solid var(--line); }
.trow.cut{ border-top:2px dotted var(--gold); }
.trow.q{ background:linear-gradient(90deg, rgba(52,211,153,.08), transparent 70%); border-radius:6px; }
.trow .tn{ font-weight:600; font-size:.95rem; }
.trow.q .tn::before{ content:"▸ "; color:var(--emerald); }
.trow .tp{ text-align:right; }
.trow .pp{ font-variant-numeric:tabular-nums; font-weight:700; color:var(--ink); font-size:.85rem; }
.trow .tk{ height:6px; border-radius:99px; background:rgba(148,163,184,.14); margin-top:.22rem; }
.trow .tk i{ display:block; height:100%; border-radius:99px; background:var(--emerald); }
.sublab{ color:var(--muted); font-size:.68rem; text-transform:uppercase; letter-spacing:.1em;
  font-weight:700; margin:.8rem 0 .25rem; }
.fx{ display:grid; grid-template-columns:6.8rem 1fr auto; gap:1rem; align-items:center;
  padding:.34rem 0; font-size:.84rem; border-top:1px dashed var(--line); }
.fx .w{ color:var(--muted); white-space:nowrap; font-variant-numeric:tabular-nums; padding-right:.3rem; }
.fx .t{ font-weight:600; }
.fx .g{ color:var(--muted); font-size:.76rem; text-align:right; }

/* Norge-kort */
.nor{ background:linear-gradient(150deg,#16243c,#0f1828); border:1px solid var(--line);
  border-radius:18px; padding:1.1rem 1.2rem; margin:.6rem 0 .2rem; }
.nor .h{ font-family:'Archivo',sans-serif; font-weight:800; font-size:1.2rem; margin-bottom:.7rem; }
.norstats{ display:grid; grid-template-columns:repeat(3,1fr); gap:.8rem; margin-bottom:.5rem; }
.norstat{ text-align:center; }
.norstat .v{ font-family:'Archivo',sans-serif; font-weight:900; font-size:1.9rem; color:var(--emerald); }
.norstat.win .v{ color:var(--gold); }
.norstat .l{ color:var(--muted); font-size:.7rem; text-transform:uppercase; letter-spacing:.08em; }

/* kamp */
.obar{ display:flex; height:42px; border-radius:12px; overflow:hidden; border:1px solid var(--line); }
.oseg{ display:grid; place-items:center; font-family:'Archivo',sans-serif; font-weight:800; color:#06281f;
  font-size:.95rem; min-width:0; }
.oseg.home{ background:linear-gradient(180deg,var(--emerald),var(--emerald-deep)); }
.oseg.draw{ background:#39455c; color:var(--ink); }
.oseg.away{ background:linear-gradient(180deg,var(--blue),#3a78c2); color:#04203f; }
.olegend{ display:flex; justify-content:space-between; color:var(--muted); font-size:.8rem; margin-top:.4rem; }
.score{ text-align:center; background:var(--surface); border:1px solid var(--line); border-radius:14px;
  padding:.8rem; margin-top:.9rem; }
.score .xg{ font-family:'Archivo',sans-serif; font-weight:900; font-size:1.6rem; }
.score .ml{ color:var(--muted); font-size:.8rem; }
.scol{ background:var(--surface); border:1px solid var(--line); border-radius:14px; padding:.7rem .9rem; }
.scol h5{ margin:.1rem 0 .5rem; font-family:'Archivo',sans-serif; }
.sline{ display:grid; grid-template-columns:1fr 3rem; gap:.5rem; align-items:center; padding:.28rem 0; }
.sline .pn{ font-size:.9rem; }
.sline .pv{ text-align:right; font-variant-numeric:tabular-nums; font-weight:700; color:var(--emerald); }
.sline .pt{ grid-column:1/3; height:5px; border-radius:99px; background:rgba(148,163,184,.14); }
.sline .pt i{ display:block; height:100%; border-radius:99px;
  background:linear-gradient(90deg,var(--emerald-deep),var(--emerald)); }
.h2h{ display:grid; grid-template-columns:6.4rem 1fr auto; gap:.5rem; padding:.3rem 0;
  border-top:1px solid var(--line); font-size:.86rem; }
.h2h .d{ color:var(--muted); font-variant-numeric:tabular-nums; }
.h2h .r{ font-family:'Archivo',sans-serif; font-weight:800; text-align:right; }

/* toppscorere */
.lb{ background:var(--surface); border:1px solid var(--line); border-radius:16px; padding:.4rem .9rem; }
.lrow{ display:grid; grid-template-columns:2rem 1fr auto; gap:.8rem; align-items:center;
  padding:.55rem 0; border-top:1px solid var(--line); }
.lrow:first-child{ border-top:none; }
.lrow .lr{ font-family:'Archivo',sans-serif; font-weight:900; text-align:center; color:var(--muted); }
.lrow.top1 .lr{ color:var(--gold);} .lrow.top2 .lr{ color:#cbd5e1;} .lrow.top3 .lr{ color:#d08a52;}
.lrow .who{ font-weight:600; } .lrow .who .tm{ color:var(--muted); font-size:.78rem; margin-left:.4rem; }
.lrow .ltk{ height:7px; border-radius:99px; background:rgba(148,163,184,.14); margin-top:.34rem; }
.lrow .ltk i{ display:block; height:100%; border-radius:99px;
  background:linear-gradient(90deg,var(--emerald-deep),var(--emerald)); }
.lrow .lv{ font-family:'Archivo',sans-serif; font-weight:800; font-variant-numeric:tabular-nums; }

/* topplista heatmap */
.heatwrap{ overflow:auto; border:1px solid var(--line); border-radius:16px; }
table.heat{ border-collapse:collapse; width:100%; font-size:.84rem; }
table.heat th{ position:sticky; top:0; background:var(--surface2); color:var(--muted);
  font-family:'Archivo',sans-serif; font-weight:700; text-transform:uppercase; letter-spacing:.05em;
  font-size:.68rem; padding:.55rem .5rem; text-align:center; border-bottom:1px solid var(--line); }
table.heat th.lft, table.heat td.lft{ text-align:left; }
table.heat td{ padding:.4rem .5rem; text-align:center; font-variant-numeric:tabular-nums;
  border-bottom:1px solid rgba(148,163,184,.07); }
table.heat td.rk{ color:var(--muted); font-family:'Archivo',sans-serif; font-weight:800; }
table.heat tr.t1 td.rk{ color:var(--gold);} table.heat tr.t2 td.rk{ color:#cbd5e1;} table.heat tr.t3 td.rk{ color:#d08a52;}
table.heat td.team{ font-weight:600; white-space:nowrap; }

/* program (kampprogram m/ prediksjoner) */
.mday{ font-family:'Archivo',sans-serif; font-weight:800; font-size:1rem; color:var(--emerald);
  margin:1.4rem 0 .55rem; padding-bottom:.3rem; border-bottom:1px solid var(--line); }
.mcard{ background:var(--surface); border:1px solid var(--line); border-radius:14px;
  padding:.7rem .9rem; margin-bottom:.6rem; }
.mtop{ display:flex; justify-content:space-between; font-size:.72rem; color:var(--muted);
  text-transform:uppercase; letter-spacing:.05em; }
.mtop .mtime{ font-weight:800; color:var(--ink); font-variant-numeric:tabular-nums; }
.mteams{ display:grid; grid-template-columns:1fr 2.6rem 1fr; align-items:center; gap:.6rem; margin-top:.45rem; }
.mteams .mt{ display:flex; align-items:center; gap:.5rem; min-width:0; }
.mteams .mt.away{ justify-content:flex-end; }
.mteams .mn{ font-family:'Archivo',sans-serif; font-weight:800; font-size:1.02rem; }
.mteams .mp{ font-variant-numeric:tabular-nums; font-weight:700; color:var(--emerald); }
.mteams .mt.away .mp{ color:var(--blue); }
.mteams .mx{ text-align:center; font-size:.64rem; color:var(--muted); line-height:1.15; }
.mbar{ display:flex; height:9px; border-radius:99px; overflow:hidden; margin:.5rem 0 .4rem; }
.mmeta{ font-size:.78rem; color:var(--muted); font-variant-numeric:tabular-nums; }
.mmeta .msc{ display:block; margin-top:.18rem; color:var(--emerald); }

/* fasit (resultat vs modell) */
.fcard{ background:var(--surface); border:1px solid var(--line); border-left:4px solid var(--muted);
  border-radius:12px; padding:.6rem .9rem; margin-bottom:.55rem; }
.fcard.hit{ border-left-color:var(--emerald); }
.fcard.miss{ border-left-color:#f2706f; }
.ftop{ display:flex; justify-content:space-between; font-size:.7rem; color:var(--muted);
  text-transform:uppercase; letter-spacing:.05em; font-variant-numeric:tabular-nums; }
.frow{ display:flex; justify-content:space-between; align-items:center; margin-top:.25rem; gap:.6rem; }
.fteam{ font-family:'Archivo',sans-serif; font-weight:800; font-size:1.02rem; }
.fmark{ font-size:1.15rem; font-weight:800; }
.fmark.y{ color:var(--emerald); }
.fmark.n{ color:#f2706f; }
.fmeta{ font-size:.78rem; color:var(--muted); margin-top:.18rem; }

/* sluttspill */
.koround{ font-family:'Archivo',sans-serif; font-weight:800; font-size:1.05rem; color:var(--gold);
  margin:1.5rem 0 .55rem; padding-bottom:.3rem; border-bottom:1px solid var(--line); }
.kocard{ background:var(--surface); border:1px solid var(--line); border-radius:12px;
  padding:.55rem .9rem; margin-bottom:.5rem; }
.koteams{ font-family:'Archivo',sans-serif; font-weight:800; font-size:1rem; margin-top:.25rem;
  display:grid; grid-template-columns:1fr auto 1fr; align-items:center; gap:.6rem; }
.koteams .ka{ text-align:right; }
.koteams .kovs{ color:var(--muted); font-weight:700; font-size:.74rem; }

/* spillerkort */
.squad{ display:grid; grid-template-columns:repeat(auto-fill,minmax(104px,1fr)); gap:.7rem; }
.pc{ background:var(--surface); border:1px solid var(--line); border-radius:14px; padding:.7rem .4rem .6rem;
  text-align:center; }
.pc .ph{ width:64px; height:64px; border-radius:50%; margin:0 auto; background-size:cover;
  background-position:center top; background-color:#22304a; border:2px solid var(--line);
  display:grid; place-items:center; font-family:'Archivo',sans-serif; font-weight:800; color:var(--muted); }
.pc .nm{ font-weight:600; font-size:.82rem; margin-top:.5rem; line-height:1.2; }
.pc .nu{ color:var(--emerald); font-weight:800; font-size:.72rem; }
.poslab{ font-family:'Archivo',sans-serif; font-weight:800; color:var(--ink); font-size:1rem;
  margin:1rem 0 .55rem; display:flex; align-items:center; gap:.5rem; }
.poslab::after{ content:""; flex:1; height:1px; background:var(--line); }
.teamstats{ display:grid; grid-template-columns:repeat(4,1fr); gap:.7rem; margin:.4rem 0 .2rem; }

/* sluttspill-tre */
.bkwrap{ overflow-x:auto; padding-bottom:.45rem; margin:.2rem 0 .4rem; }
.bk{ display:flex; gap:.5rem; min-width:max-content; }
.bkcol{ display:flex; flex-direction:column; justify-content:space-around; gap:.45rem; min-width:8.6rem; }
.bkhead{ font-size:.7rem; letter-spacing:.05em; text-transform:uppercase; color:var(--muted);
         text-align:center; margin-bottom:.25rem; font-weight:800; }
.bkm{ background:rgba(255,255,255,.035); border:1px solid var(--line); border-radius:9px; overflow:hidden; }
.bkt{ padding:.34rem .55rem; font-size:.82rem; white-space:nowrap; overflow:hidden;
      text-overflow:ellipsis; border-bottom:1px solid var(--line); }
.bkm .bkt:last-child{ border-bottom:0; }
.bkt.win{ font-weight:800; background:rgba(52,211,153,.14); }
.bkt.code{ color:var(--muted); white-space:normal; font-size:.74rem; line-height:1.22; }

/* ── mobil: la rutenettene stable seg og skalere ned ── */
@media (max-width: 760px){
  .block-container{ padding-left:.55rem; padding-right:.55rem; }
  .hero{ padding:1rem .8rem 1.1rem; border-radius:16px; }
  .hero h1{ font-size:2.05rem; }
  .hero .tag{ font-size:.86rem; }

  .tiles{ grid-template-columns:1fr !important; gap:.6rem; }
  .tile{ padding:.9rem 1rem; }
  .tile .tnum{ font-size:2.1rem; }
  .tile.kick .kteams{ font-size:1.25rem; }

  .podium{ grid-template-columns:1fr !important; gap:.6rem; }
  .pod{ padding:1rem .9rem; }
  .pod.g1{ transform:none; padding-top:1.1rem; }
  .pod .big{ font-size:2.2rem; }
  .pod.g1 .big{ font-size:2.4rem; }

  .ggrid{ grid-template-columns:1fr !important; }
  .teamstats{ grid-template-columns:repeat(2,1fr) !important; }
  .squad{ grid-template-columns:repeat(auto-fill,minmax(84px,1fr)) !important; }

  .fx{ grid-template-columns:4.6rem 1fr !important; gap:.5rem; }
  .fx .g{ display:none; }

  .stButton > button{ white-space:normal !important; font-size:.72rem;
    padding:.4rem .2rem; line-height:1.12; }

  .heatwrap{ -webkit-overflow-scrolling:touch; }
  table.heat{ font-size:.78rem; }
  .bkcol{ min-width:7.4rem; }
  .bkt{ font-size:.76rem; padding:.3rem .45rem; }
}
</style>
""", unsafe_allow_html=True)


def esc(x):
    return html.escape(str(x))


def pctf(x, d=0):
    return f"{x * 100:.{d}f}%"


# ── Flagg (emoji) for VM-lagene, nøklet på normalisert navn ──
def _fnorm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = s.replace("&", " and ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


_FLAG_ISO = {
    "mexico": "MX", "south africa": "ZA", "south korea": "KR", "czech republic": "CZ",
    "bosnia and herzegovina": "BA", "canada": "CA", "qatar": "QA", "switzerland": "CH",
    "brazil": "BR", "haiti": "HT", "morocco": "MA",
    "australia": "AU", "paraguay": "PY", "turkey": "TR", "united states": "US", "usa": "US",
    "curacao": "CW", "ecuador": "EC", "germany": "DE", "ivory coast": "CI",
    "japan": "JP", "netherlands": "NL", "sweden": "SE", "tunisia": "TN",
    "belgium": "BE", "egypt": "EG", "iran": "IR", "new zealand": "NZ",
    "cape verde": "CV", "saudi arabia": "SA", "spain": "ES", "uruguay": "UY",
    "france": "FR", "iraq": "IQ", "norway": "NO", "senegal": "SN",
    "algeria": "DZ", "argentina": "AR", "austria": "AT", "jordan": "JO",
    "colombia": "CO", "dr congo": "CD", "portugal": "PT", "uzbekistan": "UZ",
    "croatia": "HR", "ghana": "GH", "panama": "PA",
}
# England og Skottland bruker egne subdivisjons-flagg, ikke en landkode.
_FLAG_SPECIAL = {
    "england": "\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F",
    "scotland": "\U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F",
}


def flag(name):
    key = _fnorm(name)
    if key in _FLAG_SPECIAL:
        return _FLAG_SPECIAL[key]
    iso = _FLAG_ISO.get(key)
    if not iso:
        return ""
    return chr(0x1F1E6 + ord(iso[0]) - 65) + chr(0x1F1E6 + ord(iso[1]) - 65)


def tf(name):
    """Lagnavn med flagg foran (uendret hvis vi ikke har et flagg)."""
    f = flag(name)
    return f"{f} {esc(name)}" if f else esc(name)


# ── Sluttspill-tre (forsiden) ──
_BK_ROUNDS = ["Round of 32", "Round of 16", "Quarter-final", "Semi-final", "Final"]
_BK_SHORT = {"Round of 32": "32-del", "Round of 16": "16-del",
             "Quarter-final": "Kvart", "Semi-final": "Semi", "Final": "Finale"}
_BK_SOURCES = {c: (a, b) for c, a, b in tournament.TREE}
_BK_CHILD = {}
for _c, _a, _b in tournament.TREE:
    _BK_CHILD[_a] = _c
    _BK_CHILD[_b] = _c


def _bk_leaforder(n):
    if n in _BK_SOURCES:
        a, b = _BK_SOURCES[n]
        return _bk_leaforder(a) + _bk_leaforder(b)
    return [n]


_GRP_RE = re.compile(r"^([123])([A-L])$")


def _bk_concrete(v):
    """Sant hvis plassen er et ekte lag eller en gruppeplass (ikke en W/L-peker)."""
    return re.match(r"^[WL]\d+$", str(v)) is None


def _bk_short(v):
    """Kort, lesbar etikett for en plass: lag, gruppeplassering, eller 3.-plass."""
    if flag(v):
        return tf(v)
    m = _GRP_RE.match(str(v))
    if m:
        k, L = m.groups()
        pre = {"1": "vinner gr.", "2": "2er gr.", "3": "3er gr."}[k]
        return f"{pre} {L}"
    if str(v)[:1] == "3" and "/" in str(v):
        return "3.-plass"
    return esc(v)


@st.cache_data(show_spinner=False)
def _knockout_rows():
    """Sluttspillkamper med kampnummer (tom hvis 'num' ikke finnes ennå)."""
    try:
        con = duckdb.connect(getattr(common, "DB", "data/vm2026.duckdb"), read_only=True)
        df = con.execute(
            "select num, round, team1, team2 from raw_schedule "
            "where num is not null and round != 'Match for third place'"
        ).df()
        con.close()
        return df
    except Exception:
        return pd.DataFrame(columns=["num", "round", "team1", "team2"])


def _bracket_html(rows):
    if rows.empty:
        return ""
    byteam = {int(r.num): (r.team1, r.team2) for r in rows.itertuples()}
    rounds = {int(r.num): r.round for r in rows.itertuples()}
    if 104 not in byteam:
        return ""
    pos = {n: i for i, n in enumerate(_bk_leaforder(104))}

    def leafmin(n):
        return min(pos.get(le, 999) for le in _bk_leaforder(n))

    def winner(n):
        t1, t2 = byteam[n]
        c = _BK_CHILD.get(n)
        if not c or c not in byteam:
            return None
        cset = {byteam[c][0], byteam[c][1]}
        return t1 if t1 in cset else (t2 if t2 in cset else None)

    def cell(v, won):
        if flag(v):
            return f"<div class='bkt{' win' if won else ''}'>{tf(v)}</div>"
        mw = re.match(r"^([WL])(\d+)$", str(v))
        if mw:
            src = int(mw.group(2))
            wl = "Vinner" if mw.group(1) == "W" else "Taper"
            if src in byteam and all(_bk_concrete(x) for x in byteam[src]):
                s1, s2 = byteam[src]
                txt = f"{wl} av {_bk_short(s1)} – {_bk_short(s2)}"
            else:
                txt = f"{wl} kamp {src}"
            return f"<div class='bkt code'>{txt}</div>"
        return f"<div class='bkt code'>{_bk_short(v)}</div>"

    cols = ""
    for rnd in _BK_ROUNDS:
        nums = sorted([n for n in byteam if rounds.get(n) == rnd], key=leafmin)
        if not nums:
            continue
        cells = ""
        for n in nums:
            t1, t2 = byteam[n]
            w = winner(n)
            cells += f"<div class='bkm'>{cell(t1, w == t1)}{cell(t2, w == t2)}</div>"
        cols += f"<div class='bkcol'><div class='bkhead'>{_BK_SHORT[rnd]}</div>{cells}</div>"
    return f"<div class='bkwrap'><div class='bk'>{cols}</div></div>"


# ───────────────────────────── hero + nav ─────────────────────────────
st.markdown(
    "<div class='hero'>"
    "<div class='kick'>Fotball-VM · 11. juni – 19. juli 2026</div>"
    "<h1>Hvem løfter pokalen? 🏆</h1>"
    "<div class='tag'>En statistisk modell spiller hele VM tusenvis av ganger — "
    "48 lag, 104 kamper, tre vertsnasjoner — for å anslå hvor langt hvert lag kommer.</div></div>",
    unsafe_allow_html=True,
)

PAGES = ["Forside", "Grupper", "Program", "Sluttspill",
         "Toppscorere", "Topplista", "Fasit", "Metode"]
st.session_state.setdefault("page", "Forside")


def _nav(pages, per_row=5):
    for i in range(0, len(pages), per_row):
        cols = st.columns(per_row)
        for col, name in zip(cols, pages[i:i + per_row]):
            if col.button(name, width="stretch", key=f"nav_{name}",
                          type="primary" if st.session_state.page == name else "secondary"):
                st.session_state.page = name
                st.rerun()


_nav(PAGES, per_row=4)
st.write("")


# ───────────────────────────── forside ─────────────────────────────
def forside():
    today = dt.date.today()
    d_start = (dt.date(2026, 6, 11) - today).days
    d_final = (dt.date(2026, 7, 19) - today).days
    sched = common.get_schedule().sort_values("oslo")
    final_tile = (f"<div class='tile'><div class='tnum'>{max(d_final, 0)}</div>"
                  "<div class='tlab'>dager til finalen</div></div>")

    if d_start > 0:
        # Før avspark: nedtelling + åpningskamp
        nxt = sched.iloc[0]
        tiles = (
            f"<div class='tile'><div class='tnum'>{d_start}</div><div class='tlab'>dager til VM</div></div>"
            f"{final_tile}"
            "<div class='tile kick'><div class='klab'>Åpningskamp</div>"
            f"<div class='kteams'>{esc(nxt.team1)} – {esc(nxt.team2)}</div>"
            f"<div class='kmeta'>{esc(common.fmt_oslo(nxt.oslo))} norsk tid · {esc(nxt.ground)}</div></div>"
        )
    else:
        # VM i gang: fremdrift + neste kamp
        now = pd.Timestamp.now(tz="Europe/Oslo").tz_convert("UTC")
        oslo = pd.to_datetime(sched["oslo"], utc=True)
        played = int((oslo < now).sum())
        total = len(sched)
        upcoming = sched[(oslo >= now).to_numpy()]
        played_tile = (
            f"<div class='tile'><div class='tnum'>{played}"
            f"<span style='font-size:1.2rem;color:var(--muted)'> / {total}</span></div>"
            "<div class='tlab'>gruppekamper spilt</div></div>"
        )
        if not upcoming.empty:
            nxt = upcoming.iloc[0]
            kick = ("<div class='tile kick'><div class='klab'>Neste kamp</div>"
                    f"<div class='kteams'>{esc(nxt.team1)} – {esc(nxt.team2)}</div>"
                    f"<div class='kmeta'>{esc(common.fmt_oslo(nxt.oslo))} norsk tid · {esc(nxt.ground)}</div></div>")
        else:
            kick = ("<div class='tile kick'><div class='klab'>Gruppespillet</div>"
                    "<div class='kteams'>Ferdigspilt</div>"
                    "<div class='kmeta'>Sluttspillet er i gang</div></div>")
        tiles = f"{played_tile}{final_tile}{kick}"

    st.markdown(f"<div class='tiles'>{tiles}</div>", unsafe_allow_html=True)

    probs = common.get_probabilities()
    top3 = probs.head(3)
    st.markdown("<div class='section'>Antatte vinnere</div>", unsafe_allow_html=True)
    rows3 = list(top3.iterrows())
    seq = ([(2, rows3[1][1]), (1, rows3[0][1]), (3, rows3[2][1])]
           if len(rows3) >= 3 else [(i, r) for i, (_, r) in enumerate(rows3, 1)])
    cards = ""
    for rank, r in seq:
        crown = "<div class='crown'>👑</div>" if rank == 1 else ""
        cards += (
            f"<div class='pod g{rank}'>{crown}<div class='rank'>#{rank}</div>"
            f"<div class='team'>{tf(r.team)}</div>"
            f"<div class='big'>{r.champion * 100:.1f}%</div>"
            f"<div class='sub'>vinner VM · semi {pctf(r.semi)}</div></div>"
        )
    st.markdown(f"<div class='podium'>{cards}</div>", unsafe_allow_html=True)

    # Norge
    nor = probs[probs.team == "Norway"]
    sched = common.get_schedule()
    nm = sched[(sched.team1 == "Norway") | (sched.team2 == "Norway")]
    if not nor.empty:
        r = nor.iloc[0]
        grp = nm.iloc[0].letter if not nm.empty else "?"
        fx = ""
        for _, m in nm.iterrows():
            fx += (f"<div class='fx'><span class='w'>{esc(common.fmt_oslo(m.oslo))}</span>"
                   f"<span class='t'>{tf(m.team1)} – {tf(m.team2)}</span>"
                   f"<span class='g'>{esc(m.ground)}</span></div>")
        st.markdown(f"<div class='section'>🇳🇴 Norge i VM — Gruppe {esc(grp)}</div>",
                    unsafe_allow_html=True)
        st.markdown(
            "<div class='nor'>"
            "<div class='norstats'>"
            f"<div class='norstat'><div class='v'>{pctf(r.knockout)}</div><div class='l'>Videre fra gruppen</div></div>"
            f"<div class='norstat'><div class='v'>{pctf(r.semi)}</div><div class='l'>Når semifinalen</div></div>"
            f"<div class='norstat win'><div class='v'>{pctf(r.champion, 1)}</div><div class='l'>Vinner VM</div></div>"
            f"</div>{fx}</div>",
            unsafe_allow_html=True,
        )

    # sluttspill-tre
    st.write("")
    bk = _bracket_html(_knockout_rows())
    if bk:
        st.markdown("<div class='section'>Veien til finalen</div>", unsafe_allow_html=True)
        st.markdown("<div class='lead'>Hele sluttspill-treet — ekte lag fylles inn etter hvert som "
                    "rundene avgjøres, og vinneren av hver kamp markeres i grønt. "
                    "Sveip vannrett for å se hele veien.</div>", unsafe_allow_html=True)
        st.markdown(bk, unsafe_allow_html=True)

    st.markdown("<div class='section'>Om årets VM</div>", unsafe_allow_html=True)
    st.write(
        "Fotball-VM 2026 er det første med 48 lag og det første med tre vertsnasjoner. "
        "Med 104 kamper over 39 dager er det tidenes største sluttspill, og den nye "
        "32-delsfinalen betyr at et lag kan måtte spille åtte kamper for å løfte pokalen. "
        "Modellen spiller hele turneringen tusenvis av ganger for å anslå hvor langt hvert lag kommer.")
    st.caption("Tidsvektet Poisson-modell trent på ~49 000 landskamper (1872–i dag), "
               "backtestet til log-loss ≈ 0,857 (ren gjetting = 1,10). Lagnivå, ikke spillernivå.")


# ───────────────────────────── grupper ─────────────────────────────
def grupper():
    sched = common.get_schedule()
    probs = common.get_probabilities()
    adv = {common.norm(t): a for t, a in zip(probs.team, probs.knockout)}
    letters = sorted(sched.letter.unique())
    st.markdown("<div class='section'>Grupper og kampprogram</div>", unsafe_allow_html=True)
    st.markdown("<div class='lead'>Prosenten er modellens sjanse for å gå videre fra gruppen. "
                "Gull-linjen markerer kvalifiseringsgrensen (topp to). Ferdigspilte kamper viser "
                "resultatet i grønt; resten viser avspark i norsk tid.</div>",
                unsafe_allow_html=True)

    res = common.get_results_vs_model()
    score_map = {}
    for _, m in res.iterrows():
        score_map[frozenset({common.norm(m.home), common.norm(m.away)})] = (
            common.norm(m.home), int(m.ah), int(m.aa))

    cards = ""
    for L in letters:
        gm = sched[sched.letter == L]
        teams = sorted(set(gm.team1) | set(gm.team2),
                       key=lambda t: adv.get(common.norm(t), 0), reverse=True)
        trows = ""
        for k, t in enumerate(teams):
            a = adv.get(common.norm(t))
            pp = f"{a * 100:.0f}%" if a is not None else "—"
            w = (a or 0) * 100
            cls = "trow q" if k < 2 else "trow"
            if k == 2:
                cls += " cut"
            trows += (
                f"<div class='{cls}'><div class='tn'>{tf(t)}</div>"
                f"<div class='tp'><span class='pp'>{pp}</span>"
                f"<div class='tk'><i style='width:{w:.0f}%'></i></div></div></div>"
            )
        fx = ""
        for _, m in gm.iterrows():
            sc = score_map.get(frozenset({common.norm(m.team1), common.norm(m.team2)}))
            if sc is not None:
                home_norm, hs, as_ = sc
                s1, s2 = (hs, as_) if home_norm == common.norm(m.team1) else (as_, hs)
                left = f"<span class='w' style='color:var(--emerald);font-weight:800'>{s1}–{s2}</span>"
            else:
                left = f"<span class='w'>{esc(common.fmt_oslo(m.oslo))}</span>"
            fx += (f"<div class='fx'>{left}"
                   f"<span class='t'>{tf(m.team1)} – {tf(m.team2)}</span>"
                   f"<span class='g'>{esc(m.ground)}</span></div>")
        cards += (
            f"<div class='gcard'><div class='gcap'><span class='badge'>{esc(L)}</span>Gruppe {esc(L)}</div>"
            f"{trows}<div class='sublab'>Kampprogram</div>{fx}</div>"
        )
    st.markdown(f"<div class='ggrid'>{cards}</div>", unsafe_allow_html=True)


# ───────────────────────────── lag ─────────────────────────────
def lag():
    squads = common.get_squads()
    probs = common.get_probabilities()
    sched = common.get_schedule()
    teams = sorted(squads.team.unique())
    sel = st.selectbox("Velg lag", teams,
                       index=teams.index("Norway") if "Norway" in teams else 0)
    nrm = common.norm(sel)

    fx = sched[(sched.team1.apply(common.norm) == nrm) | (sched.team2.apply(common.norm) == nrm)]
    grp = fx.iloc[0].letter if not fx.empty else "?"
    prow = probs[probs.team.apply(common.norm) == nrm]

    st.markdown(f"<h2 style='margin-bottom:.2rem'>{esc(sel)}</h2>", unsafe_allow_html=True)
    if not prow.empty:
        r = prow.iloc[0]
        st.markdown(
            "<div class='teamstats'>"
            f"<div class='tile'><div class='tnum' style='font-size:1.7rem'>{esc(grp)}</div><div class='tlab'>Gruppe</div></div>"
            f"<div class='tile'><div class='tnum' style='font-size:1.7rem'>{pctf(r.knockout)}</div><div class='tlab'>Videre</div></div>"
            f"<div class='tile'><div class='tnum' style='font-size:1.7rem'>{pctf(r.semi)}</div><div class='tlab'>Semi</div></div>"
            f"<div class='tile'><div class='tnum' style='font-size:1.7rem;color:var(--gold)'>{pctf(r.champion, 1)}</div><div class='tlab'>Mester</div></div>"
            "</div>",
            unsafe_allow_html=True,
        )

    if not fx.empty:
        st.markdown("<div class='sublab'>Gruppekamper</div>", unsafe_allow_html=True)
        rows = ""
        for _, m in fx.iterrows():
            rows += (f"<div class='fx'><span class='w'>{esc(common.fmt_oslo(m.oslo))}</span>"
                     f"<span class='t'>{esc(m.team1)} – {esc(m.team2)}</span>"
                     f"<span class='g'>{esc(m.ground)}</span></div>")
        st.markdown(f"<div class='gcard'>{rows}</div>", unsafe_allow_html=True)

    order = {"Goalkeeper": "Keepere", "Defender": "Forsvar",
             "Midfielder": "Midtbane", "Attacker": "Angrep"}
    team_squad = squads[squads.team == sel]
    for pos, label in order.items():
        gp = team_squad[team_squad.position == pos]
        if gp.empty:
            continue
        st.markdown(f"<div class='poslab'>{label}</div>", unsafe_allow_html=True)
        cards = ""
        for _, p in gp.iterrows():
            uri = common.photo_uri(p.photo_file) if "photo_file" in p and pd.notna(p.photo_file) else ""
            num = f"#{int(p.number)}" if pd.notna(p.number) else ""
            initials = "".join(w[0] for w in str(p.player).split()[:2]).upper()
            ph = (f"<div class='ph' style=\"background-image:url('{uri}')\"></div>" if uri
                  else f"<div class='ph'>{esc(initials)}</div>")
            cards += (f"<div class='pc'>{ph}"
                      f"<div class='nm'><span class='nu'>{num}</span> {esc(p.player)}</div></div>")
        st.markdown(f"<div class='squad'>{cards}</div>", unsafe_allow_html=True)


# ───────────────────────────── kamp ─────────────────────────────
def kamp():
    model = common.get_model()
    teams = sorted({t for g in common.derive_groups(common.get_fixtures()) for t in g})
    st.markdown("<div class='section'>Enkeltkamp</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    home = c1.selectbox("Hjemmelag", teams,
                        index=teams.index("Norway") if "Norway" in teams else 0)
    away = c2.selectbox("Bortelag", teams,
                        index=teams.index("France") if "France" in teams else 1)
    neutral = st.checkbox("Nøytral bane", value=True)
    if home == away:
        st.warning("Velg to forskjellige lag.")
        return

    p = predict_match(model, home, away, neutral)
    tot = p["p_home"] + p["p_draw"] + p["p_away"]
    ph, pd_, pa = p["p_home"] / tot, p["p_draw"] / tot, p["p_away"] / tot
    st.markdown(
        "<div class='obar'>"
        f"<div class='oseg home' style='flex:{ph:.4f}'>{ph * 100:.0f}%</div>"
        f"<div class='oseg draw' style='flex:{pd_:.4f}'>{pd_ * 100:.0f}%</div>"
        f"<div class='oseg away' style='flex:{pa:.4f}'>{pa * 100:.0f}%</div>"
        "</div>"
        "<div class='olegend'>"
        f"<span>● {esc(home)}</span><span>uavgjort</span><span>{esc(away)} ●</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='score'><div class='xg'>{esc(home)} {p['exp_home']:.1f} – {p['exp_away']:.1f} {esc(away)}</div>"
        f"<div class='ml'>forventede mål · mest sannsynlig resultat {p['score'][0]}–{p['score'][1]}</div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='section' style='font-size:1.1rem'>Hvem scorer?</div>", unsafe_allow_html=True)
    sc = scorer_table(model, home, away, neutral)
    s1, s2 = st.columns(2)
    for col, team in [(s1, home), (s2, away)]:
        r = sc[sc.team == team]
        body = f"<h5>{esc(team)}</h5>"
        if r.empty:
            body += "<div class='ml'>Ingen ferske måldata.</div>"
        else:
            mx = float(r.p_score.max()) or 1.0
            for _, row in r.iterrows():
                body += (f"<div class='sline'><span class='pn'>{esc(row.scorer)}</span>"
                         f"<span class='pv'>{row.p_score * 100:.0f}%</span>"
                         f"<div class='pt'><i style='width:{row.p_score / mx * 100:.0f}%'></i></div></div>")
        col.markdown(f"<div class='scol'>{body}</div>", unsafe_allow_html=True)

    h2h = common.get_h2h(home, away)
    st.markdown("<div class='section' style='font-size:1.1rem'>Siste oppgjør</div>", unsafe_allow_html=True)
    if h2h.empty:
        st.markdown("<div class='lead'>Ingen tidligere oppgjør i datagrunnlaget.</div>", unsafe_allow_html=True)
    else:
        rows = ""
        for _, m in h2h.iterrows():
            rows += (f"<div class='h2h'><span class='d'>{str(m.match_date)[:10]}</span>"
                     f"<span>{esc(m.home_team)} – {esc(m.away_team)}</span>"
                     f"<span class='r'>{int(m.home_score)}–{int(m.away_score)}</span></div>")
        st.markdown(f"<div class='gcard'>{rows}</div>", unsafe_allow_html=True)


# ───────────────────────────── toppscorere ─────────────────────────────
def toppscorere():
    st.markdown("<div class='section'>Gullstøvel-kappløpet</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='lead'>Forventede mål = spillerens andel av lagets mål × lagets snitt forventede mål "
        "per kamp × forventet antall kamper laget spiller. En spiller som tar en stor andel av målene "
        "til et lag som går langt, kan derfor toppe lista foran kjente navn på sterkere lag — et anslag, ikke en fasit.</div>",
        unsafe_allow_html=True,
    )
    race = common.get_scorer_race(20)
    mx = float(race.exp_goals.max()) or 1.0
    rows = ""
    for i, (_, r) in enumerate(race.iterrows(), 1):
        cls = f"lrow top{i}" if i <= 3 else "lrow"
        rows += (
            f"<div class='{cls}'><div class='lr'>{i}</div>"
            f"<div><div class='who'>{esc(r.scorer)}<span class='tm'>{esc(r.team)}</span></div>"
            f"<div class='ltk'><i style='width:{r.exp_goals / mx * 100:.0f}%'></i></div></div>"
            f"<div class='lv'>{r.exp_goals:.2f}</div></div>"
        )
    st.markdown(f"<div class='lb'>{rows}</div>", unsafe_allow_html=True)


# ───────────────────────────── topplista ─────────────────────────────
def topplista():
    st.markdown("<div class='section'>Topplista</div>", unsafe_allow_html=True)
    st.markdown("<div class='lead'>Hvert lags sannsynlighet for å nå hver runde. Jo varmere celle, "
                "desto mer sannsynlig — kolonnene viser «veien gjennom» turneringen.</div>",
                unsafe_allow_html=True)
    cols = [("champion", "Vinner VM"), ("final", "Finale"), ("semi", "Semi"),
            ("quarter", "Kvart"), ("r16", "16-del"), ("knockout", "Sluttspill")]
    probs = common.get_probabilities()
    head = "<th class='lft'>#</th><th class='lft'>Lag</th>" + "".join(f"<th>{h}</th>" for _, h in cols)
    body = ""
    for i, (_, r) in enumerate(probs.iterrows(), 1):
        tcls = f"t{i}" if i <= 3 else ""
        cells = ""
        for key, _ in cols:
            v = float(r[key])
            alpha = min(v ** 0.7, 1.0)
            cells += f"<td style='background:rgba(52,211,153,{alpha:.3f})'>{v * 100:.1f}%</td>"
        body += (f"<tr class='{tcls}'><td class='rk'>{i}</td>"
                 f"<td class='team lft'>{esc(r.team)}</td>{cells}</tr>")
    st.markdown(
        f"<div class='heatwrap'><table class='heat'><thead><tr>{head}</tr></thead>"
        f"<tbody>{body}</tbody></table></div>",
        unsafe_allow_html=True,
    )


# ───────────────────────────── program ─────────────────────────────
_NO_WD = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"]
_NO_MON = ["", "januar", "februar", "mars", "april", "mai", "juni", "juli",
           "august", "september", "oktober", "november", "desember"]


def _daylabel(ts):
    return f"{_NO_WD[ts.weekday()]} {ts.day}. {_NO_MON[ts.month]}"


def program():
    st.markdown("<div class='section'>Kampprogram med prediksjoner</div>", unsafe_allow_html=True)
    st.markdown("<div class='lead'>Modellens anslag for hver gruppespillkamp, dag for dag. "
                "«Odds» er 1 ÷ sannsynlighet — grei å bruke i en vennekonkurranse. "
                "Sluttspillet fylles inn etter hvert som gruppene blir ferdigspilt.</div>",
                unsafe_allow_html=True)
    mp = common.get_match_predictions()
    cur, out = None, ""
    for _, m in mp.iterrows():
        label = _daylabel(m.match_date)
        if label != cur:
            cur = label
            out += f"<div class='mday'>{label}</div>"
        tot = m.p_home + m.p_draw + m.p_away
        ph, pdr, pa = m.p_home / tot, m.p_draw / tot, m.p_away / tot
        time = m.oslo.strftime("%H:%M") if m.oslo is not None else "—"
        venue = " · ".join(x for x in [m.ground or "", (f"Gr. {m.letter}" if m.letter else "")] if x)
        odds = f"{1 / ph:.2f} / {1 / pdr:.2f} / {1 / pa:.2f}"
        scs = []
        if m.top_home:
            scs.append(f"{esc(m.home)}: {esc(m.top_home)}")
        if m.top_away:
            scs.append(f"{esc(m.away)}: {esc(m.top_away)}")
        scline = (" ⚽ " + " · ".join(scs)) if scs else ""
        out += (
            "<div class='mcard'>"
            f"<div class='mtop'><span class='mtime'>{time}</span><span>{esc(venue)}</span></div>"
            "<div class='mteams'>"
            f"<div class='mt'><span class='mn'>{esc(m.home)}</span><span class='mp'>{ph * 100:.0f}%</span></div>"
            f"<div class='mx'>X<br>{pdr * 100:.0f}%</div>"
            f"<div class='mt away'><span class='mp'>{pa * 100:.0f}%</span><span class='mn'>{esc(m.away)}</span></div>"
            "</div>"
            "<div class='mbar'>"
            f"<div class='oseg home' style='flex:{ph:.4f}'></div>"
            f"<div class='oseg draw' style='flex:{pdr:.4f}'></div>"
            f"<div class='oseg away' style='flex:{pa:.4f}'></div></div>"
            f"<div class='mmeta'>Forventet {m.exp_home:.1f}–{m.exp_away:.1f} · "
            f"sannsynlig {m.score_h}–{m.score_a} · odds {odds}"
            f"<span class='msc'>{scline}</span></div>"
            "</div>"
        )
    st.markdown(out, unsafe_allow_html=True)


# ───────────────────────────── sluttspill ─────────────────────────────
ROUND_NO = {
    "Round of 32": "32-delsfinale", "Round of 16": "Åttedelsfinale",
    "Quarter-final": "Kvartfinale", "Quarter-finals": "Kvartfinale",
    "Quarter-finals": "Kvartfinale", "Semi-final": "Semifinale", "Semi-finals": "Semifinale",
    "Play-off for third place": "Bronsefinale", "Third place play-off": "Bronsefinale",
    "Match for third place": "Bronsefinale", "Final": "Finale",
}


def _slot(s):
    s = str(s)
    m = re.fullmatch(r"([12])([A-L])", s)
    if m:
        return ("Vinner" if m.group(1) == "1" else "2er") + f" Gr. {m.group(2)}"
    if re.fullmatch(r"3[A-L/]+", s):
        return "3er (Gr. " + s[1:] + ")"
    m = re.fullmatch(r"W(\d+)", s)
    if m:
        return f"Vinner kamp {m.group(1)}"
    m = re.fullmatch(r"L(\d+)", s)
    if m:
        return f"Taper kamp {m.group(1)}"
    return s


def sluttspill():
    st.markdown("<div class='section'>Sluttspill</div>", unsafe_allow_html=True)
    st.markdown("<div class='lead'>Hele veien fra 32-delsfinalen til finalen. Før gruppespillet er ferdig "
                "viser kampene plassene («Vinner Gr. A», «2er Gr. B») — de fylles inn med ekte lag etter "
                "hvert som gruppene spilles og du henter ferske data.</div>", unsafe_allow_html=True)
    ko = common.get_knockout()
    if ko.empty:
        st.markdown("<div class='lead'>Fant ingen sluttspill-kamper i kampprogrammet.</div>",
                    unsafe_allow_html=True)
        return
    omin = ko.dropna(subset=["oslo"]).groupby("round").oslo.min().sort_values()
    order = list(omin.index) + [r for r in ko["round"].unique() if r not in set(omin.index)]
    out = ""
    for rnd in order:
        sub = ko[ko["round"] == rnd]
        out += f"<div class='koround'>{esc(ROUND_NO.get(rnd, rnd))}</div>"
        for _, m in sub.iterrows():
            out += (
                "<div class='kocard'>"
                f"<div class='ftop'><span>{esc(common.fmt_oslo(m.oslo))}</span><span>{esc(m.ground)}</span></div>"
                f"<div class='koteams'><span class='ka'>{esc(_slot(m.team1))}</span>"
                f"<span class='kovs'>vs</span><span>{esc(_slot(m.team2))}</span></div>"
                "</div>"
            )
    st.markdown(out, unsafe_allow_html=True)


# ───────────────────────────── fasit ─────────────────────────────
def fasit():
    import numpy as np
    st.markdown("<div class='section'>Fasit vs modell</div>", unsafe_allow_html=True)
    df = common.get_results_vs_model()
    if df.empty:
        st.markdown("<div class='lead'>Ingen VM-kamper er spilt ennå. Etter åpningskampen — og en "
                    "datakjøring (<code>bash update.sh</code>) — dukker fasiten opp her, så ser vi "
                    "hvor godt modellen traff.</div>", unsafe_allow_html=True)
        return
    n = len(df)
    hits = int(df.hit.sum())
    exact = int(((df.ph == df.ah) & (df.pa_ == df.aa)).sum())
    logloss = float((-np.log(df.p_actual.clip(lower=1e-9))).mean())
    st.markdown(
        "<div class='tiles' style='grid-template-columns:repeat(3,1fr)'>"
        f"<div class='tile'><div class='tnum'>{hits}/{n}</div>"
        f"<div class='tlab'>riktig utfall · {hits / n * 100:.0f}%</div></div>"
        f"<div class='tile'><div class='tnum'>{exact}</div><div class='tlab'>eksakt resultat truffet</div></div>"
        f"<div class='tile'><div class='tnum' style='font-size:2rem'>{logloss:.2f}</div>"
        "<div class='tlab'>log-loss · gjetting = 1,10</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    nf = int(df.frozen.sum()) if "frozen" in df.columns else 0
    if nf == n:
        note = "Alle anslag er frosset før kampstart — en ren etterkontroll uten fasit-lekkasje."
    elif nf > 0:
        note = (f"{nf} av {n} anslag er frosset før kampstart; resten beregnes på nåværende "
                "modell og er kun omtrentlige.")
    else:
        note = ("Ingen frosne anslag funnet ennå, så disse beregnes på nåværende modell (omtrentlig). "
                "Kjør <code>uv run python ingest/snapshot.py</code> for å fryse før-kamp-anslag.")
    st.markdown(f"<div class='lead'>{note}</div>", unsafe_allow_html=True)
    out = ""
    for _, m in df.iterrows():
        cls = "hit" if m.hit else "miss"
        mark = "y" if m.hit else "n"
        sym = "✓" if m.hit else "✗"
        time = m.oslo.strftime("%d.%m %H:%M") if m.oslo is not None else ""
        gr = f"Gr. {esc(m.letter)}" if m.letter else ""
        outcomes = [(esc(m.home), m.p_home, m.pred == "H"),
                    ("uavgjort", m.p_draw, m.pred == "U"),
                    (esc(m.away), m.p_away, m.pred == "B")]
        parts = []
        for lbl, p, pick in outcomes:
            t = f"{lbl} {p * 100:.0f}%"
            parts.append(f"<b style='color:var(--ink)'>{t}</b>" if pick else t)
        meta = "Modellen ga: " + " · ".join(parts)
        out += (
            f"<div class='fcard {cls}'>"
            f"<div class='ftop'><span>{time}</span><span>{gr}</span></div>"
            f"<div class='frow'><span class='fteam'>{esc(m.home)} {m.ah}–{m.aa} {esc(m.away)}</span>"
            f"<span class='fmark {mark}'>{sym}</span></div>"
            f"<div class='fmeta'>{meta}</div>"
            "</div>"
        )
    st.markdown(out, unsafe_allow_html=True)


# ───────────────────────────── metode ─────────────────────────────
def metode():
    st.markdown("<div class='section'>Slik fungerer modellen</div>", unsafe_allow_html=True)
    st.markdown("<div class='lead'>Alt på siden kommer fra én statistisk modell trent på faktiske "
                "landskamp-resultater. Her er hva den gjør, hvorfor — og hva den bevisst ikke gjør.</div>",
                unsafe_allow_html=True)

    st.markdown("<div class='section' style='font-size:1.1rem'>Datagrunnlaget</div>", unsafe_allow_html=True)
    st.write("Modellen lærer av rundt 49 000 internasjonale landskamper fra 1872 til i dag, pluss "
             "målscorer-data og det offisielle VM-kampprogrammet. Lag med færre enn 30 kamper siden 2015 "
             "filtreres bort — det er for lite til å anslå en pålitelig styrke, og alle 48 VM-lag er godt "
             "over grensen. VM-historikk i seg selv betyr ingenting: et lag rangeres etter hvordan det "
             "faktisk har spilt nylig, ikke etter gamle meritter.")

    st.markdown("<div class='section' style='font-size:1.1rem'>Lagstyrke — tidsvektet Poisson</div>",
                unsafe_allow_html=True)
    st.write("Hvert lag får en angreps- og en forsvarsstyrke, og hjemmelag scorer litt mer — men kun på "
             "ikke-nøytral bane. Nesten alle VM-kamper er nøytrale; unntaket er vertsnasjonene (USA, Mexico, "
             "Canada) når de spiller hjemme. Forventet antall mål regnes slik:")
    st.code("forventede mål = exp( angrep[laget] + forsvar[motstanderen] + hjemmefordel )", language=None)
    st.write("Alle styrkene estimeres samtidig fra resultatene med Poisson-regresjon. Ferske kamper teller "
             "mest: en kamp vektes ned eksponentielt med alderen, med 4 års halveringstid — en verdi vi "
             "valgte objektivt ved å teste, ikke gjette.")

    st.markdown("<div class='section' style='font-size:1.1rem'>Treffsikkerhet (backtesting)</div>",
                unsafe_allow_html=True)
    st.write("Vi trener på kamper før en gitt dato og tester på de etter, og måler med log-loss (straffer "
             "selvsikre feil hardt; lavere = bedre). Ren gjetting gir ≈ 1,10.")
    bt = [("1 år", "0,8674"), ("2 år", "0,8586"), ("4 år ← valgt", "0,8569"),
          ("8 år", "0,8573"), ("ingen vekting", "0,8588")]
    trs = "".join(f"<tr><td class='lft team'>{esc(a)}</td><td>{esc(b)}</td></tr>" for a, b in bt)
    st.markdown(
        "<div class='heatwrap' style='max-width:340px'><table class='heat'>"
        "<thead><tr><th class='lft'>Halveringstid</th><th>Log-loss</th></tr></thead>"
        f"<tbody>{trs}</tbody></table></div>",
        unsafe_allow_html=True,
    )
    st.write("Modellen lander på ~0,857 — altså ekte prediktiv ferdighet. Kontroll: de sterkeste angrepene "
             "er Spania, Brasil, Belgia, Tyskland og Frankrike, og hjemmefordelen tilsvarer ~30 % flere mål. "
             "Tidsvekting hjelper bare marginalt — det største løftet ville vært bedre data, ikke en fancier "
             "algoritme.")

    st.markdown("<div class='section' style='font-size:1.1rem'>Fra kamp til turnering</div>",
                unsafe_allow_html=True)
    st.write("For én kamp bygger vi hele rutenettet av mulige resultater (0–0, 1–0, 2–1 …) og summerer til "
             "seier, uavgjort og tap. For hele VM bruker vi Monte Carlo: vi spiller turneringen tusenvis av "
             "ganger, trekker et tilfeldig resultat for hver kamp fra modellen, og teller hvor ofte hvert lag "
             "går videre, når semi og vinner. Andelen ganger blir sannsynligheten.")
    st.write("Én bevisst forenkling: sluttspill-bracketen trekkes foreløpig tilfeldig, ikke etter FIFAs faste "
             "oppsett med tredjeplass-tabellen. Det påvirker enkeltlags vei litt, men nesten ikke topp-"
             "favorittenes mester-odds. Straffekonkurranser modelleres som 50/50.")

    st.markdown("<div class='section' style='font-size:1.1rem'>Hvem scorer (gullstøvelen)</div>",
                unsafe_allow_html=True)
    st.write("Lagets forventede mål fordeles på spillerne etter hvor stor andel av lagets mål hver pleier å "
             "score, basert på fersk form. Gullstøvel-anslaget ganger denne andelen med lagets snitt "
             "forventede mål og forventet antall kamper. Derfor kan en spiller som tar en stor andel av "
             "målene til et lag som går langt (f.eks. Enner Valencia for Ecuador) havne foran kjente navn på "
             "sterkere lag som deler målene på flere — det er forventet oppførsel av regnestykket, ikke en feil.")

    st.markdown("<div class='section' style='font-size:1.1rem'>Hva modellen ikke vet</div>",
                unsafe_allow_html=True)
    st.write("Den er på lagnivå, ikke spillernivå: den kjenner ikke skader, formkurver eller troppkvalitet ut "
             "over hva resultatene viser. Derfor rangerer den f.eks. Frankrike lavere enn bookmakerne — den "
             "ser aggregerte ferske mål, ikke at troppen er eksepsjonell. Tenk på den som en ærlig, kalibrert "
             "baseline, ikke et orakel. Vær mest skeptisk der troppkvalitet og resultater spriker.")


{"Forside": forside, "Grupper": grupper, "Program": program, "Sluttspill": sluttspill,
 "Toppscorere": toppscorere, "Topplista": topplista,
 "Fasit": fasit, "Metode": metode}[st.session_state.page]()