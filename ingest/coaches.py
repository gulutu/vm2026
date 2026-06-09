"""Henter NÅVÆRENDE trener per VM-lag og oppdaterer raw_coaches."""
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


def current_coach(coaches, team_id):
    for c in coaches:                                  # 1) trener hvis NÅVÆRENDE lag er dette laget
        if (c.get("team") or {}).get("id") == team_id:
            return c
    for c in coaches:                                  # 2) trener med pågående periode (end = null)
        for s in c.get("career", []):
            if (s.get("team") or {}).get("id") == team_id and s.get("end") is None:
                return c
    best, bs = None, ""                                # 3) ellers nyeste start hos laget
    for c in coaches:
        for s in c.get("career", []):
            if (s.get("team") or {}).get("id") == team_id and (s.get("start") or "") > bs:
                bs, best = s.get("start") or "", c
    return best or (coaches[0] if coaches else None)


def main():
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    teams = [(t["team"]["id"], t["team"]["name"])
             for t in api("teams", league=LEAGUE, season=SEASON)]
    rows = []
    for tid, tname in teams:
        c = current_coach(api("coachs", team=tid), tid)
        if c:
            cid = c.get("id")
            local = download_photo(c.get("photo"), PHOTO_DIR / f"coach_{cid}.png") if cid else None
            rows.append({"team": tname, "coach": c.get("name"), "age": c.get("age"),
                         "photo_url": c.get("photo"), "photo_file": local})
        print(f"  {tname:<24} {c.get('name') if c else '—'}")
        time.sleep(1)
    con = duckdb.connect(DB)
    con.register("c_df", pd.DataFrame(rows))
    con.execute("CREATE OR REPLACE TABLE raw_coaches AS SELECT * FROM c_df")
    con.close()
    print(f"\nOppdatert raw_coaches: {len(rows)} trenere")


if __name__ == "__main__":
    main()