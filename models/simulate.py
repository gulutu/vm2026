"""Monte Carlo-simulering av VM-gruppespillet."""
from collections import defaultdict
import numpy as np
import pandas as pd
from poisson import load_matches, filter_teams, add_weights, to_long, fit, load_fixtures

N = 10000  # antall gjennomspillinger

def expected_goals(model, home, away, neutral):
    rows = pd.DataFrame({"team": [home, away], "opponent": [away, home],
                         "home_adv": [0 if neutral else 1, 0]})
    return model.predict(rows).to_numpy()  # [lambda_hjemme, mu_borte]

def derive_groups(fixtures):
    """Utled de 12 gruppene fra kampoppsettet (lag som møtes er i samme gruppe)."""
    adj = defaultdict(set)
    for _, m in fixtures.iterrows():
        adj[m.home_team].add(m.away_team)
        adj[m.away_team].add(m.home_team)
    groups, seen = [], set()
    for team in adj:
        if team in seen:
            continue
        g = sorted({team} | adj[team])
        groups.append(g)
        seen |= set(g)
    return groups

if __name__ == "__main__":
    model = fit(to_long(add_weights(filter_teams(load_matches()))))
    fixtures = load_fixtures()
    groups = derive_groups(fixtures)
    teams = sorted({t for g in groups for t in g})

    # Akkumuler poeng / målforskjell / scorede mål per lag over alle N gjennomspillinger
    pts = {t: np.zeros(N, dtype=int) for t in teams}
    gd  = {t: np.zeros(N, dtype=int) for t in teams}
    gf  = {t: np.zeros(N, dtype=int) for t in teams}

    rng = np.random.default_rng()
    for _, m in fixtures.iterrows():
        lam, mu = expected_goals(model, m.home_team, m.away_team, m.neutral)
        hg, ag = rng.poisson(lam, N), rng.poisson(mu, N)
        pts[m.home_team] += np.where(hg > ag, 3, np.where(hg == ag, 1, 0))
        pts[m.away_team] += np.where(ag > hg, 3, np.where(hg == ag, 1, 0))
        gd[m.home_team] += hg - ag; gd[m.away_team] += ag - hg
        gf[m.home_team] += hg;      gf[m.away_team] += ag

    print(f"Gruppespill-simulering ({N:,} gjennomspillinger)\n")
    for n, g in enumerate(groups, start=1):
        # Sammensatt nøkkel: poeng veier mest, så målforskjell, så scorede mål
        score = np.vstack([pts[t] * 1_000_000 + (gd[t] + 100) * 1_000 + gf[t] for t in g])
        rank = np.argsort(np.argsort(-score, axis=0), axis=0)  # 0 = 1.plass per simulering
        rows = [(t, (rank[i] == 0).mean(), (rank[i] <= 1).mean()) for i, t in enumerate(g)]
        rows.sort(key=lambda r: -r[2])
        print(f"Gruppe {n}:")
        for t, p_win, p_adv in rows:
            print(f"  {t:<24} videre {p_adv:5.0%}   (vinner gruppen {p_win:4.0%})")
        print()