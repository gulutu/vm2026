# VM 2026 — Fotballprediksjon

Privat læringsprosjekt: en statistisk modell som predikerer fotball-VM 2026 —
kamputfall, gruppespill og hvem som vinner turneringen. Bygget som en datapipeline
(ingest → DuckDB → dbt → modell → simulering) med en interaktiv Streamlit-app som er
deployet i skyen og kan oppdateres midt i mesterskapet.

**Live:** `https://<din-app>.streamlit.app` (Streamlit Community Cloud)

## Hva den gjør

- **Enkeltkamper:** sannsynlighet for seier/uavgjort/tap, forventede mål og mest
  sannsynlig resultat
- **Gruppespill:** simulerer turneringen tusenvis av ganger (Monte Carlo) → hvert lags
  sjanse for å gå videre fra gruppen
- **Hele turneringen:** simulerer frem til finalen → sannsynlighet for hver runde og for
  å bli mester
- **Toppscorere:** en gullstøvel-modell basert på spillernes andel av landslagets mål
- **Fasit vs modell:** fryser modellens anslag *før* kampstart og måler dem mot de
  faktiske resultatene (riktig utfall + log-loss) — en ren etterkontroll uten
  fasit-lekkasje
- **Oppdaterbar midt i VM:** nye resultater inn → modellen re-trenes, og simuleringen
  låser inn de faktisk spilte kampene og trekker bare de gjenstående tilfeldig

## Appen

Mørkt «matchday»-tema med ti sider: Forside, Grupper, Program, Sluttspill, Lag, Kamp,
Toppscorere, Topplista, Fasit og Metode. Kjører lokalt under utvikling og er deployet på
Streamlit Community Cloud for visning på telefon/web.

## Hvordan det henger sammen

```
Data (martj42, openfootball, API-Football)
   → DuckDB → dbt (staging → marts) → Poisson-modell → Monte Carlo → Streamlit
```

1. **Ingest** (`ingest/`): ~49 000 landskamper (1872–i dag) og målscorere fra
   martj42, kampoppsettet fra openfootball, og tropper/spillerbilder fra API-Football,
   lastet inn i DuckDB.
2. **dbt** (`dbt/`): renser dataene og deler dem i spilte kamper (treningsdata) og
   kommende kamper (prediksjonsmål). Bygger marts `fct_matches`, `fct_fixtures` og
   `player_goal_share` fra staging-modellen `stg_matches`.
3. **Modell** (`models/poisson.py`): tidsvektet Poisson-regresjon.
4. **Simulering** (`models/tournament.py`): spiller hele turneringen mange ganger;
   `models/scorers.py` regner gullstøvel-løpet.
5. **App** (`app/app.py` + `app/common.py`): Streamlit-grensesnittet.

## Modellen

Hvert lag har en **angrepsstyrke** og en **forsvarsstyrke**, og hjemmelaget scorer litt
mer (kun på ikke-nøytral bane — nesten alle VM-kamper spilles nøytralt). Forventet antall
mål:

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
antar hjemme- og bortemål uavhengige (ingen Dixon-Coles-korreksjon); lag med
< 30 landskamper siden 2015 filtreres bort; sluttspillet bruker foreløpig en forenklet
(tilfeldig) bracket blant de 32 kvalifiserte. Spilte gruppekamper låses derimot til sitt
faktiske resultat i simuleringen.

## Oppdatere midt i VM

Hjemme på utviklingsmaskinen, én kommando for datajobben:

```bash
bash update.sh   # frys anslag → hent resultater, målscorere og program → dbt run
```

`update.sh` fryser først modellens anslag for kommende kamper (til Fasit, slik at det
ikke lekker fasit), henter så ferske data og bygger dbt-martene på nytt. For å få det ut
på den deployede appen:

```bash
git add data/vm2026.duckdb
git commit -m "Oppdater resultater"
git pull --rebase
git push          # → Streamlit Community Cloud bygger seg om automatisk
```

## Kjør lokalt

```bash
uv sync                                              # installer avhengigheter
uv run python ingest/results.py                      # hent data → DuckDB
cd dbt && uv run dbt run --profiles-dir . && cd ..   # transformér (dbt)
uv run python models/poisson.py                      # kampprediksjoner (rask sjekk)
uv run python models/tournament.py                   # hele turneringen → mester
uv run streamlit run app/app.py                      # start appen
```

## Struktur

```
vm2026/
├── data/
│   ├── raw/            # landingssone for rådata (CSV/JSON)
│   ├── photos/         # spillerbilder (committet for deploy)
│   └── vm2026.duckdb   # database (committet for deploy)
├── ingest/             # datainnsamling + snapshot.py (frys anslag)
├── dbt/                # dbt-prosjekt (staging → marts)
├── models/             # poisson.py, tournament.py, scorers.py
├── app/                # Streamlit: app.py + common.py
├── update.sh           # full oppdateringspipeline i én kommando
├── requirements.txt    # avhengigheter for Streamlit Community Cloud
└── pyproject.toml      # uv-konfigurasjon
```

## Stack

Python 3.12 (uv) · DuckDB · dbt-duckdb · pandas · statsmodels / scipy ·
Streamlit (Community Cloud)

## Status & veikart

- [x] Datapipeline: ingest → dbt → marts
- [x] Tidsvektet Poisson-modell, backtestet mot historikk
- [x] Gruppespill- og turneringssimulering (videre + mester)
- [x] Gullstøvel-modell (andel av lagets mål)
- [x] Streamlit-app (ti sider) deployet på Streamlit Community Cloud
- [x] Oppdateringsflyt (`update.sh`) + frosne før-kamp-anslag (Fasit)
- [x] Simulering som låser inn faktisk spilte gruppekamper
- [ ] Ekte sluttspill-bracket (FIFAs tredjeplass-logikk) — erstatter dagens tilfeldige bracket