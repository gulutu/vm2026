"""Henter VM 2026-kampprogrammet (openfootball, public domain) til DuckDB."""
import json
from pathlib import Path

import duckdb
import httpx
import pandas as pd

URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
RAW = Path("data/raw/wc2026_schedule.json")
DB = "data/vm2026.duckdb"


def download():
    RAW.parent.mkdir(parents=True, exist_ok=True)
    print(f"Laster ned {URL} ...")
    r = httpx.get(URL, timeout=30, follow_redirects=True)
    r.raise_for_status()
    RAW.write_bytes(r.content)
    print(f"Lagret {RAW} ({len(r.content) / 1024:.0f} KB)")


def load():
    data = json.loads(RAW.read_text(encoding="utf-8"))
    rows = [{"num": m.get("num"), "round": m.get("round"), "date": m.get("date"),
             "time": m.get("time"), "grp": m.get("group"), "team1": m.get("team1"),
             "team2": m.get("team2"), "ground": m.get("ground")} for m in data["matches"]]
    df = pd.DataFrame(rows)
    con = duckdb.connect(DB)
    con.register("sched_df", df)
    con.execute("CREATE OR REPLACE TABLE raw_schedule AS SELECT * FROM sched_df")
    n = con.execute("select count(*) from raw_schedule").fetchone()[0]
    g = con.execute("select count(*) from raw_schedule where grp is not null").fetchone()[0]
    k = con.execute("select count(*) from raw_schedule where num is not null").fetchone()[0]
    print(f"\nraw_schedule: {n} kamper ({g} i gruppespillet, {k} med kampnummer)")
    con.close()


if __name__ == "__main__":
    download()
    load()