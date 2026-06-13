"""Fryser modellens prediksjon for kommende kamper, slik at Fasit-siden kan
sammenligne mot et ekte FØR-kamp-anslag — uten fasit-lekkasje fra at modellen
senere trenes på resultatet.

Kjør fra prosjektroten:
    uv run python ingest/snapshot.py

Skriver til tabellen `model_predictions` i data/vm2026.duckdb. Skriptet er
idempotent: en kamp fryses bare FØRSTE gang den ses (mens den fortsatt er en
kommende kamp i fct_fixtures), så et tidligere anslag overskrives aldri. Kjør
det gjerne før hver `update.sh` — da fanges også sluttspillkamper når de dukker
opp med ekte lag.
"""
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "models"))

import duckdb
from poisson import load_matches, filter_teams, add_weights, to_long, fit, predict_match

DB = str(ROOT / "data" / "vm2026.duckdb")
ALIASES = {"usa": "united states", "czechia": "czech republic", "cabo verde": "cape verde",
           "cape verde islands": "cape verde", "cote divoire": "ivory coast",
           "congo dr": "dr congo", "korea republic": "south korea", "turkiye": "turkey"}


def norm(name):
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return ALIASES.get(s, s)


def match_key(a, b):
    return "|".join(sorted([norm(a), norm(b)]))


def main():
    # Bygg modellen først; load_matches åpner og lukker sin egen tilkobling,
    # så vi unngår å holde to skrivelåser på samme fil samtidig.
    print("Trener modellen ...")
    model = fit(to_long(add_weights(filter_teams(load_matches()))))

    con = duckdb.connect(DB)
    con.execute(
        """
        create table if not exists model_predictions (
            match_key varchar, home_team varchar, away_team varchar, neutral boolean,
            match_date varchar, p_home double, p_draw double, p_away double,
            exp_home double, exp_away double, score_h integer, score_a integer,
            snapshot_ts timestamp
        )
        """
    )
    existing = set(con.execute("select match_key from model_predictions").df().match_key)
    fx = con.execute("select * from fct_fixtures").df()
    has_neutral = "neutral" in fx.columns
    ts = datetime.now()

    new = 0
    for _, m in fx.iterrows():
        k = match_key(m.home_team, m.away_team)
        if k in existing:
            continue
        neutral = bool(m.neutral) if has_neutral else True
        p = predict_match(model, m.home_team, m.away_team, neutral)
        con.execute(
            "insert into model_predictions values (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [k, m.home_team, m.away_team, neutral, str(m.match_date)[:10],
             float(p["p_home"]), float(p["p_draw"]), float(p["p_away"]),
             float(p["exp_home"]), float(p["exp_away"]),
             int(p["score"][0]), int(p["score"][1]), ts],
        )
        existing.add(k)
        new += 1

    total = con.execute("select count(*) from model_predictions").fetchone()[0]
    con.close()
    print(f"Frøs {new} nye kamp-anslag. Totalt {total} frosne prediksjoner i loggen.")
    if new == 0:
        print("(Ingen nye kommende kamper å fryse — alt er allerede fanget.)")


if __name__ == "__main__":
    main()