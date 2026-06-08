"""Henter historiske målscorere og lander dem i DuckDB."""
from pathlib import Path
import httpx
import duckdb

URL = "https://raw.githubusercontent.com/martj42/international_results/master/goalscorers.csv"
RAW = Path("data/raw/goalscorers.csv")
DB = "data/vm2026.duckdb"

def download() -> None:
    RAW.parent.mkdir(parents=True, exist_ok=True)
    print(f"Laster ned {URL} ...")
    resp = httpx.get(URL, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    RAW.write_bytes(resp.content)
    print(f"Lagret {RAW} ({len(resp.content) / 1024:.0f} KB)")

def load() -> None:
    con = duckdb.connect(DB)
    con.execute(f"""
        CREATE OR REPLACE TABLE raw_goalscorers AS
        SELECT * FROM read_csv_auto('{RAW}', header=true, nullstr='NA')
    """)
    n = con.execute("SELECT count(*) FROM raw_goalscorers").fetchone()[0]
    print(f"\nraw_goalscorers: {n} mål registrert")
    print("\nNorges toppscorere siden 2022:")
    print(con.execute("""
        SELECT scorer, count(*) AS mal
        FROM raw_goalscorers
        WHERE team = 'Norway' AND date >= '2022-01-01' AND not own_goal
        GROUP BY scorer ORDER BY mal DESC LIMIT 5
    """).df())
    con.close()

if __name__ == "__main__":
    download()
    load()