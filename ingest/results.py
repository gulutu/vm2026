"""Henter historiske landskampresultater og lander dem i DuckDB."""
from pathlib import Path
import httpx
import duckdb

# Åpent, aktivt vedlikeholdt datasett (martj42/international_results)
URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
RAW = Path("data/raw/results.csv")
DB = "data/vm2026.duckdb"

# henter CSV-en og lagrer rådataen i data/raw/ slik at vi slipper å laste den ned på nytt og kan inspisere den
def download() -> None:
    RAW.parent.mkdir(parents=True, exist_ok=True)
    print(f"Laster ned {URL} ...")
    resp = httpx.get(URL, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    RAW.write_bytes(resp.content)
    print(f"Lagret {RAW} ({len(resp.content) / 1024:.0f} KB)")

# Load leser inn dataen i DuckDB med DuckDB sin egen CSV-leser og skriver ut en kontroll - antall kamper,
# datospennet, og de fem nyeste kampene
def load() -> None:
    con = duckdb.connect(DB)
    con.execute(f"""
        CREATE OR REPLACE TABLE raw_results AS
        SELECT * FROM read_csv_auto('{RAW}', header=true, nullstr='NA')
    """)
    n, first, last = con.execute(
        "SELECT count(*), min(date), max(date) FROM raw_results"
    ).fetchone()
    print(f"\nraw_results: {n} kamper, fra {first} til {last}")
    print(con.execute("SELECT * FROM raw_results ORDER BY date DESC LIMIT 5").df())
    con.close()

if __name__ == "__main__":
    download()
    load()