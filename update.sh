#!/usr/bin/env bash
# Fryser før-kamp-anslag, henter ferske VM-data og bygger dbt-martene på nytt.
# Kjør fra prosjektroten:  bash update.sh
# Start deretter appen på nytt (Ctrl+C) så cachen tømmes.
set -e

echo "1/5 · Fryser modell-anslag for kommende kamper ..."
uv run python ingest/snapshot.py

echo "2/5 · Resultater (martj42) ..."
uv run python ingest/results.py

echo "3/5 · Målscorere (martj42) ..."
uv run python ingest/goalscorers.py

echo "4/5 · Kampprogram (openfootball) ..."
uv run python ingest/wc_schedule.py

echo "5/5 · dbt (staging -> marts) ..."
cd dbt && uv run dbt run --profiles-dir . && cd ..

echo ""
echo "Ferdig. Anslag for kommende kamper er frosset FØR resultatene kom inn,"
echo "nye resultater er i fct_matches, og martene er bygd på nytt. Start appen"
echo "på nytt for å tømme cachen:  uv run streamlit run app/app.py"