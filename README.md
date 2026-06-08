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
