# VM 2026 — Fotballprediksjon

Privat læringsprosjekt: en statistisk modell som predikerer fotball-VM 2026 —
kamputfall, gruppespill, og hvem som vinner turneringen.

## Hva den gjør

- **Enkeltkamper:** sannsynlighet for seier/uavgjort/tap + mest sannsynlig resultat
- **Gruppespill:** simulerer gruppespillet tusenvis av ganger (Monte Carlo) → hvert lags
  sjanse for å gå videre og for å vinne gruppen
- **Hele turneringen:** simulerer frem til finalen → sannsynlighet for å bli mester
- **Oppdaterbar midt i VM:** nye resultater inn → modellen re-trenes → nye prediksjoner

## Hvordan det henger sammen

```
Data → DuckDB → dbt (staging → marts) → Poisson-modell → simulering
```

1. **Ingest** (`ingest/`): ~49 000 landskamper (1872–i dag) + de kommende VM-kampene,
   fra et åpent, vedlikeholdt datasett, lastet inn i DuckDB.
2. **dbt** (`dbt/`): renser dataene og deler dem i spilte kamper (treningsdata) og
   kommende kamper (prediksjonsmål). Dekker dagens 48-lags felt.
3. **Modell** (`models/poisson.py`): tidsvektet Poisson-regresjon.
4. **Simulering** (`models/simulate.py`, `models/simulate_tournament.py`): spiller
   gruppespillet og hele turneringen mange ganger.

## Modellen

Hvert lag har en **angrepsstyrke** og en **forsvarsstyrke**, og hjemmelag scorer litt
mer (kun på ikke-nøytral bane). Forventet antall mål:

```
forventede mål = exp( angrep[laget] + forsvar[motstanderen] + hjemmefordel )
```

Mål antas Poisson-fordelt, og alle styrkene estimeres samtidig fra historiske resultater
med Poisson-regresjon — med større vekt på ferske kamper (eksponentiell tidsvekting,
halveringstid 4 år, valgt objektivt via backtesting). Fra de forventede målene bygges
hele rutenettet av mulige resultater, som summeres til seier/uavgjort/tap.

**Kvalitet:** backtestet til log-loss ≈ 0,857 (ren gjetting = 1,10) — reell prediktiv
ferdighet. Kontroll: topp angrep = Spania/Brasil/Belgia/Tyskland/Frankrike;
hjemmefordel ≈ 30 %.

**Bevisste forenklinger:** lagnivå, ikke spillernivå (kjenner ikke skader/troppsuttak);
antar hjemme- og bortemål uavhengige (ingen Dixon-Coles-korreksjon ennå); lag med
< 30 landskamper siden 2015 filtreres bort; sluttspillet bruker foreløpig en forenklet
(tilfeldig) bracket.

## Kjør selv

```bash
uv sync                                              # installer avhengigheter
uv run python ingest/results.py                      # hent data → DuckDB
cd dbt && uv run dbt run --profiles-dir . && cd ..   # transformér (dbt)
uv run python models/poisson.py                      # kampprediksjoner
uv run python models/simulate.py                     # gruppespill-simulering
uv run python models/simulate_tournament.py          # hele turneringen → mester
uv run python models/backtest.py                     # mål treffsikkerhet
```

## Struktur

- `ingest/` — skript som henter data
- `dbt/` — transformasjon (staging → marts)
- `models/` — `poisson.py` (modell), `simulate.py` + `simulate_tournament.py` (Monte Carlo), `backtest.py` (evaluering)
- `data/` — lokal DuckDB-database (ikke i git)

## Stack

Python 3.12 (uv) · DuckDB · dbt-duckdb · pandas · statsmodels / scipy

## Status & veikart

- [x] Datapipeline: ingest → dbt → marts
- [x] Poisson-modell med tidsvekting, backtestet
- [x] Gruppespill-simulering (sannsynlighet for å gå videre)
- [x] Turneringssimulering → mester-sannsynlighet
- [ ] Ekte sluttspill-bracket (FIFAs tredjeplass-tabell)
- [ ] Spillernivå / målscorer-modell
- [ ] Verdi mot bookmaker-odds
- [ ] Streamlit-app + automatisk oppdateringsflyt
