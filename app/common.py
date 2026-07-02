"""Delte hjelpefunksjoner for VM 2026-appen (modell, simulering, data)."""
import base64
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "models"))

import duckdb
import pandas as pd
import streamlit as st

from poisson import load_matches, filter_teams, add_weights, to_long, fit, predict_match
import tournament

DB = "data/vm2026.duckdb"
PHOTO_DIR = Path("data/photos")
OSLO = ZoneInfo("Europe/Oslo")
_NO_DAYS = ["man", "tir", "ons", "tor", "fre", "lør", "søn"]
ALIASES = {"usa": "united states", "czechia": "czech republic", "cabo verde": "cape verde",
           "cape verde islands": "cape verde", "cote divoire": "ivory coast",
           "congo dr": "dr congo", "korea republic": "south korea", "turkiye": "turkey"}


def norm(name):
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return ALIASES.get(s, s)


def to_oslo(date_str, time_str):
    m = re.match(r"(\d{1,2}):(\d{2})\s*UTC([+-]\d+)", str(time_str))
    if not m:
        return None
    hh, mm, off = int(m[1]), int(m[2]), int(m[3])
    local = datetime(*map(int, str(date_str).split("-")), hh, mm,
                     tzinfo=timezone(timedelta(hours=off)))
    return local.astimezone(OSLO)


def fmt_oslo(d):
    return f"{_NO_DAYS[d.weekday()]} {d.day:02d}.{d.month:02d} · {d:%H:%M}" if d is not None else "TBD"


@st.cache_data
def photo_uri(filename):
    """Leser et lokalt spillerbilde og returnerer en data-URI (for innbygging i HTML)."""
    try:
        if not filename or not isinstance(filename, str):
            return ""
        p = PHOTO_DIR / filename
        if not p.exists():
            return ""
        return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()
    except Exception:
        return ""


@st.cache_resource
def get_model():
    return fit(to_long(add_weights(filter_teams(load_matches()))))


@st.cache_data
def get_fixtures():
    con = duckdb.connect(DB, read_only=True)
    fx = con.execute("select * from fct_fixtures").df()
    con.close()
    return fx


@st.cache_data
def get_schedule():
    con = duckdb.connect(DB, read_only=True)
    df = con.execute("select round, date, time, grp, team1, team2, ground from raw_schedule").df()
    con.close()
    df = df[df.grp.notna()].copy()
    df["oslo"] = [to_oslo(d, t) for d, t in zip(df.date, df.time)]
    df["letter"] = df.grp.str.replace("Group ", "", regex=False)
    return df.sort_values("oslo")


@st.cache_data
def get_squads():
    con = duckdb.connect(DB, read_only=True)
    df = con.execute("select * from raw_squads").df()
    con.close()
    return df


@st.cache_data(show_spinner="Simulerer turneringen ...")
def get_probabilities(n=4000):
    return tournament.simulate(get_model(), n=n)


@st.cache_data(show_spinner="Beregner toppscorer-kappløpet ...")
def get_scorer_race(top=15):
    """Forventede mål per spiller gjennom hele turneringen."""
    model = get_model()
    probs = get_probabilities()
    teams = list(probs.team)
    eg, idx = tournament.expected_goals_matrix(model, teams)
    n = len(teams)
    avg_goals = {t: eg[idx[t]].sum() / (n - 1) for t in teams}
    exp_matches = {r.team: 3 + r.knockout + r.r16 + r.quarter + r.semi + r.final
                   for _, r in probs.iterrows()}
    con = duckdb.connect(DB, read_only=True)
    shares = con.execute("select team, scorer, share from player_goal_share").df()
    con.close()
    shares = shares[shares.team.isin(set(avg_goals))].copy()
    shares["exp_goals"] = [s * avg_goals[t] * exp_matches.get(t, 3.0)
                           for t, s in zip(shares.team, shares.share)]
    return shares.sort_values("exp_goals", ascending=False).head(top).reset_index(drop=True)


@st.cache_data
def get_h2h(a, b, n=6):
    """Siste innbyrdes oppgjør mellom to lag (fra spilte kamper)."""
    con = duckdb.connect(DB, read_only=True)
    df = con.execute(
        """
        select match_date, home_team, away_team, home_score, away_score
        from fct_matches
        where (home_team = ? and away_team = ?) or (home_team = ? and away_team = ?)
        order by match_date desc
        limit ?
        """,
        [a, b, b, a, n],
    ).df()
    con.close()
    return df


def derive_groups(fixtures):
    adj = defaultdict(set)
    for _, m in fixtures.iterrows():
        adj[m.home_team].add(m.away_team)
        adj[m.away_team].add(m.home_team)
    groups, seen = [], set()
    for t in sorted(adj):
        if t in seen:
            continue
        g = sorted({t} | adj[t])
        groups.append(g)
        seen |= set(g)
    return groups


@st.cache_data(show_spinner="Beregner kamp-prediksjoner ...")
def get_match_predictions():
    """Modellens prediksjon for hver gruppespillkamp + tid/sted + toppscorer per lag."""
    model = get_model()
    fx = get_fixtures().copy()
    sched = get_schedule()
    meta = {frozenset({norm(m.team1), norm(m.team2)}): (m.oslo, m.ground, m.letter)
            for _, m in sched.iterrows()}
    con = duckdb.connect(DB, read_only=True)
    sh = con.execute("select team, scorer, share from player_goal_share").df()
    con.close()
    top_scorer = (sh.sort_values("share", ascending=False)
                    .drop_duplicates("team").set_index("team").scorer.to_dict())
    has_neutral = "neutral" in fx.columns
    rows = []
    for _, m in fx.iterrows():
        neutral = bool(m.neutral) if has_neutral else True
        p = predict_match(model, m.home_team, m.away_team, neutral)
        oslo, ground, letter = meta.get(
            frozenset({norm(m.home_team), norm(m.away_team)}), (None, None, None))
        rows.append({
            "match_date": pd.to_datetime(m.match_date), "oslo": oslo, "ground": ground, "letter": letter,
            "home": m.home_team, "away": m.away_team,
            "p_home": float(p["p_home"]), "p_draw": float(p["p_draw"]), "p_away": float(p["p_away"]),
            "exp_home": float(p["exp_home"]), "exp_away": float(p["exp_away"]),
            "score_h": int(p["score"][0]), "score_a": int(p["score"][1]),
            "top_home": top_scorer.get(m.home_team, ""), "top_away": top_scorer.get(m.away_team, ""),
        })
    df = pd.DataFrame(rows)
    df["t"] = [o.isoformat() if o is not None else d.isoformat()
               for o, d in zip(df.oslo, df.match_date)]
    return df.sort_values("t").reset_index(drop=True)


@st.cache_data(show_spinner="Sammenligner resultater mot modellen ...")
def get_results_vs_model():
    """Spilte VM-gruppekamper med modellens prediksjon mot faktisk resultat.
    Bruker frosne før-kamp-anslag (model_predictions) der de finnes, ellers
    en live-beregning på nåværende modell."""
    model = get_model()
    sched = get_schedule()
    con = duckdb.connect(DB, read_only=True)
    played = con.execute(
        """
        select match_date, home_team, away_team, home_score, away_score
        from fct_matches
        where match_date between '2026-06-11' and '2026-07-20'
          and home_score is not null
        """
    ).df()
    tbls = set(con.execute("select table_name from information_schema.tables").df().table_name)
    frozen = con.execute("select * from model_predictions").df() if "model_predictions" in tbls else None
    con.close()

    pidx = {}
    for _, r in played.iterrows():
        pidx.setdefault(frozenset({norm(r.home_team), norm(r.away_team)}), r)
    fidx = {}
    if frozen is not None:
        for _, r in frozen.iterrows():
            fidx.setdefault(frozenset({norm(r.home_team), norm(r.away_team)}), r)

    rows = []
    for _, m in sched.iterrows():
        key = frozenset({norm(m.team1), norm(m.team2)})
        a = pidx.get(key)
        if a is None:
            continue
        fr = fidx.get(key)
        if fr is not None:
            if norm(fr.home_team) == norm(a.home_team):
                ph, pdr, paw, sh, sa = fr.p_home, fr.p_draw, fr.p_away, int(fr.score_h), int(fr.score_a)
            else:
                ph, pdr, paw, sh, sa = fr.p_away, fr.p_draw, fr.p_home, int(fr.score_a), int(fr.score_h)
            frozen_flag = True
        else:
            p = predict_match(model, a.home_team, a.away_team, True)
            ph, pdr, paw = p["p_home"], p["p_draw"], p["p_away"]
            sh, sa = int(p["score"][0]), int(p["score"][1])
            frozen_flag = False
        po = {"H": float(ph), "U": float(pdr), "B": float(paw)}
        pred = max(po, key=po.get)
        actual = "H" if a.home_score > a.away_score else ("U" if a.home_score == a.away_score else "B")
        rows.append({
            "oslo": m.oslo, "letter": m.letter,
            "home": a.home_team, "away": a.away_team,
            "ah": int(a.home_score), "aa": int(a.away_score),
            "ph": sh, "pa_": sa,
            "pred": pred, "hit": pred == actual,
            "p_home": po["H"], "p_draw": po["U"], "p_away": po["B"], "p_actual": po[actual],
            "frozen": frozen_flag,
        })
    return pd.DataFrame(rows)


@st.cache_data
def get_knockout():
    """Sluttspill-kampene fra kampprogrammet (gruppefelt er tomt for utslagsrunder)."""
    con = duckdb.connect(DB, read_only=True)
    df = con.execute(
        "select round, date, time, team1, team2, ground from raw_schedule where grp is null"
    ).df()
    con.close()
    df["oslo"] = [to_oslo(d, t) for d, t in zip(df.date, df.time)]
    return df.sort_values("oslo")


@st.cache_data
def get_knockout_results():
    """{uordnet lagpar: (hjemmelag, hjemmemål, bortemål)} for spilte sluttspillkamper."""
    con = duckdb.connect(DB, read_only=True)
    df = con.execute(
        f"""
        select home_team, away_team, home_score, away_score
        from fct_matches
        where tournament = 'FIFA World Cup' and match_date > '{tournament.GROUP_TO}'
        """
    ).df()
    con.close()
    return {frozenset({norm(r.home_team), norm(r.away_team)}): (norm(r.home_team), int(r.home_score), int(r.away_score))
            for r in df.itertuples()}