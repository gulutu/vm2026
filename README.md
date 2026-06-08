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

## Hva vi har bygget
 
Fra en maskin uten utviklingsverktøy til en fungerende prediktor, i denne rekkefølgen:
 
1. **Utviklingsmiljø:** uv (Python 3.12), VS Code, git med SSH til et privat GitHub-repo.
2. **Datapipeline:** rådata → DuckDB → dbt (staging → marts).
3. **Modell:** en Poisson-styrkemodell som gir faktiske kampprediksjoner.
### Datapipelinen i korthet
 
- **Ingest** (`ingest/results.py`): henter ~49 000 landskamper (1872–i dag) fra et
  åpent, aktivt vedlikeholdt datasett, og lander dem i DuckDB. Datasettet inneholder
  også de kommende VM-kampene — med tomt resultat (NULL) inntil de spilles.
- **dbt staging** (`stg_matches`): renser dataene og merker hver kamp med `is_played`
  — spilt eller ikke.
- **dbt marts:**
  - `fct_matches` — kun spilte kamper (~49 373). Dette er **treningsdataene**.
  - `fct_fixtures` — de 72 kommende gruppekampene. Dette er **prediksjonsmålene**.
    (12 grupper × 6 kamper = 72; sluttspillkampene dukker opp etter hvert som
    gruppene avgjøres.) Til sammen dekker de nøyaktig dagens 48-lags VM-felt.
- **Oppdaterbar:** pipelinen er idempotent. Midt i VM kan den kjøres på nytt — ferske
  resultater kommer inn, og modellen re-predikerer det som gjenstår.
---
 
## Modellen forklart
 
### Intuisjonen
 
Hvert lag får to tall: en **angrepsstyrke** (hvor mange mål de pleier å lage) og en
**forsvarsstyrke** (hvor mange de pleier å slippe inn). I tillegg scorer hjemmelag litt
mer enn bortelag. Antall mål i en kamp er tilfeldig, men styrt av disse styrkene: et
sterkt angrep mot et svakt forsvar gir høyt forventet antall mål.
 
### Det tekniske
 
**1. Mål er Poisson-fordelte.** Antall mål et lag scorer modelleres som en
Poisson-fordeling — fordelingen for «antall sjeldne hendelser i et tidsrom», som passer
mål godt. Den har én parameter, λ (forventet antall mål):
 
```
P(k mål) = λ^k · e^(−λ) / k!
```
 
**2. Forventede mål kommer fra styrkene** (en log-lineær modell):
 
```
Hjemmelag:  λ = exp( grunnivå + angrep[hjemme] + forsvar[borte] + hjemmefordel )
Bortelag:   μ = exp( grunnivå + angrep[borte]  + forsvar[hjemme] )
```
 
`exp(...)` sikrer at forventede mål alltid er positive, og gjør at styrkene virker
*multiplikativt* (et lag dobbelt så sterkt i angrep lager omtrent dobbelt så mange mål).
Hjemmefordel legges kun til når kampen **ikke** spilles på nøytral bane — viktig, siden
de fleste landskamper, og nesten alle VM-kamper, er nøytrale.
 
**3. Styrkene estimeres samtidig** med Poisson-regresjon (en GLM). Hver kamp gjøres om
til to observasjoner — ett perspektiv per lag — så én regresjon kan lære både angrep og
forsvar for alle lag på én gang, ut fra de historiske resultatene.
 
### Fra styrker til prediksjon
 
For en gitt kamp regner vi ut λ og μ, og bygger så hele rutenettet av resultater under
antakelsen om at hjemme- og bortemål er uavhengige:
 
```
P(hjemme = i, borte = j) = Poisson(i; λ) · Poisson(j; μ)
```
 
Deretter summerer vi cellene:
 
- **Hjemmeseier:** alle celler der i > j
- **Uavgjort:** der i = j
- **Borteseier:** der i < j
Det gir sannsynlighetene for seier/uavgjort/tap, og den høyeste enkeltcellen er det mest
sannsynlige eksakte resultatet.
 
### Hva modellen faktisk lærte (kontroll)
 
- **Hjemmefordel ≈ 0,26** (log) → hjemmelag scorer omtrent 30 % flere mål. Realistisk.
- **Topp angrep:** Spania, Brasil, Belgia, Tyskland, Frankrike, Argentina, Portugal …
  altså den faktiske fotballeliten — ikke støy.
- **Norge:** rangeres som konkurransedyktig (klar favoritt mot Irak, jevnt mot Senegal,
  underdog mot Frankrike), basert på fersk form — *ikke* på VM-historikk. Modellen bryr
  seg ikke om at Norge var borte fra VM i 28 år; den ser bare på resultatene de siste årene.
---
 
## Viktige forenklinger i denne versjonen (v1)
 
Disse er bevisste, og forbedres senere:
 
- **Ferskhets-grense** (kamper siden 2015) i stedet for gradvis tidsvekting.
- **Ingen Dixon-Coles-korreksjon** ennå (en justering for at lavscorende resultater som
  0–0 og 1–1 er litt vanligere enn ren Poisson tilsier).
- **Antar uavhengighet** mellom hjemme- og bortemål.
- **Lagnivå, ikke spillernivå** — modellen «vet» ikke om Haaland spesifikt, skader eller
  troppsuttak. Derfor kan den undervurdere topp-spissers effekt litt.
- **Filtrerer bort lag med < 30 kamper** i perioden — for få kamper gir upålitelige
  estimater (og velter dessuten optimeringen numerisk).
---
 
## Teknisk stack
 
Python 3.12 (uv) · DuckDB · dbt-duckdb · pandas · statsmodels / scipy · git/GitHub
 
## Neste steg
 
**v2** med tidsvekting (ferske kamper teller mer) → Dixon-Coles-korreksjonen →
**turneringssimulering** (Monte Carlo: sannsynlighet for at hvert lag går videre/vinner)
→ oppdateringsflyt + Streamlit-app for å bla i prediksjonene.
