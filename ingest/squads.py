"""Henter VM 2026-tropper, trenere og spillerbilder fra API-Football til DuckDB.

Krever en nøkkel med 2026-tilgang (PRO). Legg den i .env: API_FOOTBALL_KEY=...
~1 teams-kall + 48 squads + 48 coachs (godt innenfor 7500/dag). Bilder lastes
ned lokalt til data/photos/ og teller ikke mot kvoten.
"""
import os
import time
from pathlib import Path

import duckdb
import httpx
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
KEY = os.environ["API_FOOTBALL_KEY"]
BASE = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": KEY}
LEAGUE, SEASON = 1, 2026
DB = "data/vm2026.duckdb"
PHOTO_DIR = Path("data/photos")


def api(path, **params):
    r = httpx.get(f"{BASE}/{path}", headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get("errors"):
        raise SystemExit(f"API-feil ({path}): {data['errors']}")
    return data["response"]


def download_photo(url, dest):
    if dest.exists():
        return dest.name
    if not url:
        return None
    try:
        r = httpx.get(url, timeout=30, follow_redirects=True)
        r.raise_for_status()
        dest.write_bytes(r.content)
        return dest.name
    except Exception:
        return None


def main():
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    teams = [(t["team"]["id"], t["team"]["name"])
             for t in api("teams", league=LEAGUE, season=SEASON)]
    print(f"Fant {len(teams)} lag i VM {SEASON}.")
    if not teams:
        raise SystemExit("0 lag — har nøkkelen din PRO-tilgang til 2026?")

    players, coaches = [], []
    for tid, tname in teams:
        squad = api("players/squads", team=tid)
        roster = squad[0].get("players", []) if squad else []
        for p in roster:
            pid = p.get("id")
            local = download_photo(p.get("photo"), PHOTO_DIR / f"player_{pid}.png") if pid else None
            players.append({"team": tname, "player_id": pid, "player": p.get("name"),
                            "number": p.get("number"), "position": p.get("position"),
                            "age": p.get("age"), "photo_url": p.get("photo"), "photo_file": local})
        cs = api("coachs", team=tid)
        if cs:
            c = cs[0]
            cid = c.get("id")
            local = download_photo(c.get("photo"), PHOTO_DIR / f"coach_{cid}.png") if cid else None
            coaches.append({"team": tname, "coach": c.get("name"), "age": c.get("age"),
                            "photo_url": c.get("photo"), "photo_file": local})
        print(f"  {tname:<24} {len(roster)} spillere")
        time.sleep(1)

    con = duckdb.connect(DB)
    con.register("p_df", pd.DataFrame(players))
    con.register("c_df", pd.DataFrame(coaches))
    con.execute("CREATE OR REPLACE TABLE raw_squads AS SELECT * FROM p_df")
    con.execute("CREATE OR REPLACE TABLE raw_coaches AS SELECT * FROM c_df")
    np_ = con.execute("select count(*) from raw_squads").fetchone()[0]
    nt = con.execute("select count(distinct team) from raw_squads").fetchone()[0]
    con.close()
    print(f"\nraw_squads: {np_} spillere, {nt} lag · raw_coaches: {len(coaches)} trenere")
    print(f"Bilder lastet ned til {PHOTO_DIR}/")


if __name__ == "__main__":
    main()