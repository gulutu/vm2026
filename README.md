# VM 2026 — Fotballprediksjonsmodell

Privat læringsprosjekt: en modell som predikerer kamputfall, målscorere og
verdi mot bookmaker-odds for fotball-VM 2026.

## Stack
- Python 3.12 (styrt av `uv`)
- DuckDB — lokal lagring
- dbt-duckdb — transformasjon (staging → marts)
- Dixon-Coles målmodell + Monte Carlo turneringssimulering
- Streamlit — visning

## Kom i gang
\`\`\`bash
uv sync
\`\`\`

## Struktur
- `ingest/` — skript som henter data
- `dbt/` — transformasjon
- `models/` — prediksjonsmodeller
- `app/` — Streamlit-app
- `notebooks/` — utforsking
- `data/` — lokal data (ikke i git)

## Log

### FASE 0 (19:34 8.06) 
Så langt har vi bygget:
- `uv` som styrer prosjektpinnet Python, frikoblet fra systemet og conda
- **VS Code** koblet ti `.venv`, med Python, Ruff og Jupyter
- **git + SSH** til GitHub med verifisert vertsnøkkel og passphrase i nøkkelringen
- et **privat repo** med ren `.gitignore`, fornuftig struktur og to commits i historikken

