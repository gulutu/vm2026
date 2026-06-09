"""VM 2026 — prediksjonsmodell. Én side med topp-navigasjon (mørkt matchday-tema)."""
import datetime as dt
import html

import pandas as pd
import streamlit as st

import common
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
.hero{ text-align:center; padding:.4rem 0 1rem; }
.hero .ball{ font-size:1.5rem; }
.hero h1{ font-size:2.5rem; font-weight:900; margin:.1rem 0 .15rem;
  background:linear-gradient(92deg,#fff 30%,var(--emerald)); -webkit-background-clip:text;
  background-clip:text; -webkit-text-fill-color:transparent; }
.hero .tag{ color:var(--muted); font-size:.9rem; letter-spacing:.04em; }

/* nav pills */
.stButton > button{ border-radius:999px; font-weight:700; font-family:'Archivo',sans-serif;
  border:1px solid var(--line); background:var(--surface2); color:var(--muted); }
.stButton > button:hover{ border-color:var(--emerald); color:var(--ink); }

/* stat tiles */
.tiles{ display:grid; grid-template-columns:1fr 1fr 1.6fr; gap:.8rem; margin:.2rem 0 1.1rem; }
.tile{ background:var(--surface); border:1px solid var(--line); border-radius:16px;
  padding:1rem 1.1rem; text-align:center; }
.tile .tnum{ font-family:'Archivo',sans-serif; font-weight:900; font-size:2.6rem; line-height:1;
  color:var(--emerald); }
.tile .tlab{ color:var(--muted); font-size:.74rem; text-transform:uppercase; letter-spacing:.09em;
  margin-top:.35rem; }
.tile.kick{ text-align:left; display:flex; flex-direction:column; justify-content:center; }
.tile.kick .klab{ color:var(--gold); font-size:.7rem; text-transform:uppercase; letter-spacing:.1em;
  font-weight:700; }
.tile.kick .kteams{ font-family:'Archivo',sans-serif; font-weight:800; font-size:1.35rem; margin:.15rem 0; }
.tile.kick .kmeta{ color:var(--muted); font-size:.82rem; }

.section{ font-family:'Archivo',sans-serif; font-weight:800; font-size:1.25rem; margin:1.4rem 0 .2rem; }
.lead{ color:var(--muted); font-size:.86rem; margin-bottom:.7rem; }

/* podium */
.podium{ display:grid; grid-template-columns:repeat(3,1fr); gap:.9rem; }
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
.gcap{ display:flex; align-items:center; gap:.55rem; font-family:'Archivo',sans-serif; font-weight:800;
  font-size:1.1rem; margin-bottom:.6rem; }
.gcap .badge{ width:1.8rem; height:1.8rem; display:grid; place-items:center; border-radius:9px;
  background:var(--emerald); color:#06281f; font-weight:900; }
.trow{ display:grid; grid-template-columns:1fr 4.2rem; align-items:center; gap:.6rem; padding:.34rem 0; }
.trow + .trow{ border-top:1px solid var(--line); }
.trow.cut{ border-top:2px solid var(--gold); }
.trow .tn{ font-weight:600; font-size:.95rem; }
.trow.q .tn::before{ content:"▸ "; color:var(--emerald); }
.trow .tp{ text-align:right; }
.trow .pp{ font-variant-numeric:tabular-nums; font-weight:700; color:var(--ink); font-size:.85rem; }
.trow .tk{ height:6px; border-radius:99px; background:rgba(148,163,184,.14); margin-top:.22rem; }
.trow .tk i{ display:block; height:100%; border-radius:99px; background:var(--emerald); }
.sublab{ color:var(--muted); font-size:.68rem; text-transform:uppercase; letter-spacing:.1em;
  font-weight:700; margin:.8rem 0 .25rem; }
.fx{ display:grid; grid-template-columns:6.4rem 1fr auto; gap:.5rem; align-items:center;
  padding:.28rem 0; font-size:.84rem; border-top:1px dashed var(--line); }
.fx .w{ color:var(--muted); white-space:nowrap; font-variant-numeric:tabular-nums; }
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
</style>
""", unsafe_allow_html=True)


def esc(x):
    return html.escape(str(x))


def pctf(x, d=0):
    return f"{x * 100:.{d}f}%"


# ───────────────────────────── hero + nav ─────────────────────────────
st.markdown(
    "<div class='hero'><div class='ball'>⚽</div>"
    "<h1>VM 2026</h1>"
    "<div class='tag'>PREDIKSJONSMODELL · 48 LAG · USA · CANADA · MEXICO</div></div>",
    unsafe_allow_html=True,
)

PAGES = ["Forside", "Grupper", "Lag", "Kamp", "Toppscorere", "Topplista"]
st.session_state.setdefault("page", "Forside")
for col, name in zip(st.columns(len(PAGES)), PAGES):
    if col.button(name, width="stretch",
                  type="primary" if st.session_state.page == name else "secondary"):
        st.session_state.page = name
        st.rerun()
st.write("")


# ───────────────────────────── forside ─────────────────────────────
def forside():
    today = dt.date.today()
    d_start = (dt.date(2026, 6, 11) - today).days
    d_final = (dt.date(2026, 7, 19) - today).days
    nxt = common.get_schedule().iloc[0]

    start_txt = d_start if d_start > 0 else "I GANG"
    st.markdown(
        "<div class='tiles'>"
        f"<div class='tile'><div class='tnum'>{start_txt}</div><div class='tlab'>dager til VM</div></div>"
        f"<div class='tile'><div class='tnum'>{max(d_final, 0)}</div><div class='tlab'>dager til finalen</div></div>"
        "<div class='tile kick'><div class='klab'>Åpningskamp</div>"
        f"<div class='kteams'>{esc(nxt.team1)} – {esc(nxt.team2)}</div>"
        f"<div class='kmeta'>{esc(common.fmt_oslo(nxt.oslo))} norsk tid · {esc(nxt.ground)}</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )

    probs = common.get_probabilities()
    top3 = probs.head(3)
    st.markdown("<div class='section'>Favoritter</div>", unsafe_allow_html=True)
    cards = ""
    for i, (_, r) in enumerate(top3.iterrows(), 1):
        cards += (
            f"<div class='pod g{i}'><div class='rank'>#{i}</div>"
            f"<div class='team'>{esc(r.team)}</div>"
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
                   f"<span class='t'>{esc(m.team1)} – {esc(m.team2)}</span>"
                   f"<span class='g'>{esc(m.ground)}</span></div>")
        st.markdown(
            f"<div class='nor'><div class='h'>🇳🇴 Norge i VM — Gruppe {esc(grp)}</div>"
            "<div class='norstats'>"
            f"<div class='norstat'><div class='v'>{pctf(r.knockout)}</div><div class='l'>Videre fra gruppen</div></div>"
            f"<div class='norstat'><div class='v'>{pctf(r.semi)}</div><div class='l'>Når semifinalen</div></div>"
            f"<div class='norstat win'><div class='v'>{pctf(r.champion, 1)}</div><div class='l'>Vinner VM</div></div>"
            f"</div>{fx}</div>",
            unsafe_allow_html=True,
        )

    # to lister
    st.write("")
    left, right = st.columns(2)
    maxc = float(probs.champion.max()) or 1.0
    with left:
        st.markdown("<div class='section' style='font-size:1.05rem'>Resten av topp 10</div>", unsafe_allow_html=True)
        rows = ""
        for i, (_, r) in enumerate(probs.iloc[3:10].iterrows(), 4):
            rows += (
                f"<div class='srow'><div class='rk'>{i}</div>"
                f"<div><span class='nm'>{esc(r.team)}<span class='meta'>semi {pctf(r.semi)}</span></span>"
                f"<div class='track'><div class='fill' style='width:{r.champion / maxc * 100:.0f}%'></div></div></div>"
                f"<div class='val'>{r.champion * 100:.1f}%</div></div>"
            )
        st.markdown(f"<div class='rows'>{rows}</div>", unsafe_allow_html=True)
    with right:
        st.markdown("<div class='section' style='font-size:1.05rem'>Lengst odds</div>", unsafe_allow_html=True)
        bot = probs.tail(8).sort_values("champion")
        rows = ""
        for _, r in bot.iterrows():
            rows += (
                f"<div class='srow'><div class='rk'></div>"
                f"<div><span class='nm'>{esc(r.team)}<span class='meta'>vinner {pctf(r.champion, 1)}</span></span>"
                f"<div class='track'><div class='fill' style='width:{r.knockout * 100:.0f}%'></div></div></div>"
                f"<div class='val' style='font-size:.95rem'>{pctf(r.knockout)}</div></div>"
            )
        st.markdown(f"<div class='rows'>{rows}</div>", unsafe_allow_html=True)
        st.markdown("<div class='lead' style='margin-top:.4rem'>Bjelken viser sjansen for å gå videre fra gruppen.</div>",
                    unsafe_allow_html=True)

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
                "Gull-linjen markerer kvalifiseringsgrensen (topp to). Alle klokkeslett i norsk tid.</div>",
                unsafe_allow_html=True)

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
                f"<div class='{cls}'><div class='tn'>{esc(t)}</div>"
                f"<div class='tp'><span class='pp'>{pp}</span>"
                f"<div class='tk'><i style='width:{w:.0f}%'></i></div></div></div>"
            )
        fx = ""
        for _, m in gm.iterrows():
            fx += (f"<div class='fx'><span class='w'>{esc(common.fmt_oslo(m.oslo))}</span>"
                   f"<span class='t'>{esc(m.team1)} – {esc(m.team2)}</span>"
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


{"Forside": forside, "Grupper": grupper, "Lag": lag, "Kamp": kamp,
 "Toppscorere": toppscorere, "Topplista": topplista}[st.session_state.page]()