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
import streamlit as st

from poisson import load_matches, filter_teams, add_weights, to_long, fit
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