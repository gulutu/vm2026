# Modell-logg — VM 2026

En løpende logg over hva vi har prøvd, hva som funket, hva som ikke gjorde det, og
hvorfor. README er oversikten over det ferdige; *denne* fila er historikken og
begrunnelsene.

---

## Datagrunnlag

**Kilde:** ~49 000 internasjonale landskamper (martj42-datasettet), 1872–i dag, inkl. de
kommende VM-kampene (NULL-resultat inntil de spilles).

**Filtrering — lag med < 30 kamper siden 2015 fjernes.**
- *Hvorfor:* første forsøk trente på alle lag → Poisson-optimeringen divergerte
  (`NaN ... weights, estimation infeasible`), fordi små nasjoner med få kamper og
  ekstreme resultater (10–0 o.l.) ga ustabile koeffisienter.
- *Lærdom:* en pålitelig styrke kan ikke estimeres fra en håndfull kamper. Alle 48
  VM-lag klarer 30-grensen med god margin.

---

## Modell v1 — Poisson (angrep/forsvar/hjemmefordel)

**Hva:** log-lineær Poisson-regresjon. Hver kamp → to rader (ett perspektiv per lag), så
én regresjon estimerer angrep og forsvar for alle lag samtidig. Hjemmefordel kun på
ikke-nøytral bane.

**Resultat (kontroll):**
- Hjemmefordel ≈ 0,26 (log) → ~30 % flere mål hjemme. Realistisk.
- Topp angrep: Spania, Brasil, Belgia, Tyskland, Frankrike … = fotballeliten. ✅
- Enkeltkamp-prediksjoner stemte med magefølelsen (Sveits klar favoritt mot Qatar osv.).

**Forenklinger:** ferskhets-grense (kamper siden 2015) i stedet for vekting; ingen
Dixon-Coles; antar hjemme- og bortemål uavhengige; lagnivå (ikke spillere).

---

## Modell v2 — tidsvekting

**Hva:** eksponentiell tidsvekting, `vekt = 0,5^(alder / halveringstid)`, matet inn som
`freq_weights` i regresjonen. Ferske kamper teller mer.

**Øyemål:** Marokko og Canada krøp opp (sterk fersk form) — så lovende ut.

**MEN backtesting avslørte at gevinsten var marginal** (se under).
*Lærdom: ikke stol på øyemål — mål det.*

---

## Backtesting

**Metode:** tren på kamper før 2024-06-01, test på de etter. Score = log-loss på 1X2
(lavere = bedre). Referanse: ren gjetting = ln(3) ≈ 1,10.

| Halveringstid | Log-loss |
|---|---|
| 1 år | 0,8674 |
| 2 år | 0,8586 |
| **4 år** | **0,8569**  ← best |
| 8 år | 0,8573 |
| ingen vekting (≈ v1) | 0,8588 |

**Lærdom:**
- Modellen har ekte ferdighet (~0,857 langt under 1,10).
- Tidsvekting hjelper bare marginalt (~0,002). Vår v2-gjetning på 2 år var i praksis like
  god som ingen vekting i det hele tatt.
- 1 års halveringstid var *for* aggressivt og gjorde det verre.
- **Beslutning:** halveringstid = 4 år. Større poeng: denne knappen er nær taket sitt —
  fremtidige gevinster ligger i nye data/funksjoner, ikke i mer finjustering.

---

## Simulering — gruppespill

**Hva:** Monte Carlo, 10 000 gjennomspillinger av gruppespillet → sannsynlighet for å gå
videre / vinne gruppen.

**Resultat:** favorittene øverst i hver gruppe, internt konsistent (videre-tallene
summerer ~200 % per gruppe siden to går videre). Sverige lavt (39 %) — realistisk gitt
svak fersk form, ikke gammel rykte.

---

## Simulering — hele turneringen

**Hva:** Monte Carlo, 5 000 komplette VM (gruppespill + 5 utslagsrunder) →
mester-sannsynlighet.

**Resultat (topp):** Spania 13,6 %, Argentina 12,6 %, Brasil 11,3 %, England 8,5 %,
Portugal 7,4 %, Frankrike 6,8 % … Norge 1,3 % (semifinale 7,9 %).

**Debatterbart / å følge med på:**
- Frankrike kun 6. (6,8 %) og Colombia høyt (4,4 %). Modellen rangerer på *aggregerte
  ferske mål*, ikke troppkvalitet, så den kan avvike fra ekspert-/bookmaker-konsensus
  som rangerer Frankrike høyere. Et spillernivå-lag ville trolig justert dette.

**Forenkling:** tilfeldig sluttspill-bracket (ikke FIFAs faste bracket + tredjeplass-
tabell); straffekonkurranse modellert som 50/50.

---

## Åpne spørsmål / å teste videre

- **Ekte sluttspill-bracket** (FIFAs tredjeplass-tabell) — vil endre enkeltlags vei,
  neppe topp-favorittene mye.
- **Dixon-Coles-korreksjon** — sannsynligvis også marginal (som tidsvekting).
- **Spillernivå / skader / tropp** — trolig den største reelle forbedringen (ville
  fanget Haaland-effekten, Frankrikes kvalitet osv.).
- **Sammenligne mester-odds mot bookmakernes** for å se hvor modellen avviker.
  
## Modell — målscorer (v1)

**Hva:** lagets forventede mål × spillerens andel av lagets mål (siden 2022)
→ P(score) = 1 − e^(−forventede mål).

**Resultat:** Haaland 38 % og Mbappé 42 % i Norge–Frankrike — mekanikken funker.

**Kjent svakhet:** andelene bygger på *nylige scorere, ikke bekreftet tropp*.
Avgåtte/ikke-uttatte spillere (Giroud, Dønnum) dukker opp som artefakter, og uttatte
spillere får litt for lav andel. Fiks krever offisielle 26-mannstropper + navnematching.

**Oppdatert:** andelene strammet til fersk form (siden sep. 2024). Fjerner avgåtte/
inaktive spillere (Giroud, Dønnum) og speiler dagens scorere. Restfeil: ingen hard
garanti for nøyaktig 26-mannstropp — krever offisielle tropper + navnematching.