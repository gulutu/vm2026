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

## Plan for gjennomføring
**Hovedmål:** Bygge en kalibrert prediksjonsmodell (Dixon-Coles) for VM 2026, med fokus på moderne verktøy, ryddig arkitektur og en gradvis overgang fra lokalt miljø til skyen.

---

### Teknisk Stack & Arkitektur

| Komponent | Teknologi | Rolle i prosjektet |
| :--- | :--- | :--- |
| **Pakkehåndtering** | `uv` (Python 3.12) | Lynrask og ryddig håndtering av venv og avhengigheter. |
| **Lagring (Dev)** | **DuckDB** (lokalt) | Rask, gratis og null oppsett under iterasjon. |
| **Transformasjon**| **dbt** (`dbt-duckdb` / `dbt-bigquery`) | Analytics engineering, datarens og modellering. |
| **Prediksjon** | `scipy`, `statsmodels`, `pandas` | Statistisk modellering (Dixon-Coles) og simulering. |
| **Grensesnitt** | **Streamlit** (lokalt) | Rask prototyping og visualisering av prediksjoner. |
| **Lagring (Prod)** | **Google BigQuery** | Sky-datavarehus for endelig serving og læringssløyfe. |
| **BI / Rapport** | **Looker Studio** | Skybasert dashboard mot BigQuery. |

### Prosjektstruktur
```
vm2026/
├── .venv/              # Lokalt virtuelt miljø (styrt av uv)
├── data/
│   ├── raw/            # Landingssone for rådata (Parquet/CSV)
│   └── vm2026.duckdb   # Den lokale utviklingsdatabasen
├── ingest/             # Python-skript for datainnsamling (APIs/Kaggle)
├── dbt/                # dbt-prosjekt (staging- og marts-modeller)
├── models/             # Dixon-Coles, Elo og Monte Carlo-simulering
├── app/                # Streamlit-applikasjon
├── notebooks/          # Ad-hoc analyse og utforsking
├── pyproject.toml      # uv-konfigurasjon og avhengigheter
└── README.md           # Prosjektdokumentasjon
```

### Faser
**Fase 0: Miljø & Infrastruktur**

Aktiviteter: Sette opp prosjektet med uv, konfigurere VS Code (Python, Ruff, Jupyter) og initiere Git. Sette opp dedikert SSH-nøkkel/alias på GitHub adskilt fra jobb-profil.

Milestone: uv run python fungerer, og første commit er pushet til et privat GitHub-repo.

**Fase 1: Datainnsamling (ingest/)**

Aktiviteter: Skrive Python-skript som henter historiske resultater (Kaggle), Elo-ratinger, xG/spillerdata (via soccerdata) og markedsodds (The Odds API). Laste alt som råtabeller i DuckDB.

Milestone: Alle eksterne datakilder er tilgjengelige i vm2026.duckdb.

**Fase 2: Datatransformasjon (dbt/)**

Aktiviteter: Sette opp dbt-duckdb. Bygge staging-lag (vaske data, standardisere lagnavn til FIFA-koder og fikse typer) og marts-lag (én bred kamptabell + lag/spiller-features). Implementere datakvalitetstester.

Milestone: dbt build kjører grønt med feilfrie tester, og en analyseklar mart er klar.

**Fase 3: Statistisk Modellering (models/)**

Aktiviteter: Implementere Dixon-Coles baseline (angreps-/forsvarsstyrke per lag, tidsvekting). Backteste modellen mot historikk og bookmaker-odds (måles på log-loss/Brier). Utvide med spillertilgjengelighet og en scorermodell basert på xG-andel.

Milestone: Modellen er kalibrert og presterer beviselig bedre enn en naiv baseline.

**Fase 4: Simulering & Lokalt Grensesnitt (app/)**

Aktiviteter: Utføre Monte Carlo-simuleringer (N tusen iterasjoner av VM) for å beregne avansements- og vinnersannsynligheter. Beregne "verdi/edge" mot markedsodds (med sunn skepsis). Bygge en Streamlit-app for å visualisere resultatene.

Milestone: Interaktiv Streamlit-app kjører lokalt og viser fullstendige turneringsprediksjoner.

**Fase 5: Skyen & Servering (GCP)**

Aktiviteter: Opprette GCP-prosjekt og BigQuery-datasett. Sette opp en ny dbt-target mot BigQuery og flytte datatransformasjonen dit. Koble Looker Studio til BigQuery for et skybasert dashboard.

Milestone: Dashboardet er live i skyen og oppdateres fra BigQuery.

**Fase 6: AI-Agent (Valgfritt overtidsprosjekt)**

Aktiviteter: Integrere en LLM-agent som henter siste nyheter, skader og lagoppstillinger, justerer modellens input-paramatere, og genererer kampoppsummeringer i naturlig språk.

Milestone: Agenten kan generere automatiske, innsiktsfulle pre-match-rapporter.

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
