"""Importerbar turneringssimulering: sannsynlighet per lag for hver runde.

Kjør direkte for en rask kontroll:  uv run python models/tournament.py
Ellers: importer simulate() fra appen.
"""
from collections import defaultdict

import numpy as np
import pandas as pd

from poisson import load_matches, filter_teams, add_weights, to_long, fit, load_fixtures

N_DEFAULT = 5000


def derive_groups(fixtures):
    adj = defaultdict(set)
    for _, m in fixtures.iterrows():
        adj[m.home_team].add(m.away_team)
        adj[m.away_team].add(m.home_team)
    groups, seen = [], set()
    for t in sorted(adj):
        if t in seen:
            continue
        g = sorted({t} | adj[t])
        groups.append(g)
        seen |= set(g)
    return groups


def expected_goals_matrix(model, teams):
    """Forventede mål for alle lagpar på nøytral bane."""
    idx = {t: i for i, t in enumerate(teams)}
    rows = pd.DataFrame([(a, b) for a in teams for b in teams if a != b],
                        columns=["team", "opponent"])
    rows["home_adv"] = 0
    rows["eg"] = model.predict(rows).to_numpy()
    eg = np.zeros((len(teams), len(teams)))
    for a, b, v in zip(rows.team, rows.opponent, rows.eg):
        eg[idx[a], idx[b]] = v
    return eg, idx


def simulate(model=None, n=N_DEFAULT, seed=None):
    """Simulerer hele VM n ganger. Returnerer DataFrame med sannsynlighet per lag
    for å nå hver runde, sortert på mester-sannsynlighet."""
    if model is None:
        model = fit(to_long(add_weights(filter_teams(load_matches()))))
    fixtures = load_fixtures()
    groups = derive_groups(fixtures)
    teams = sorted({t for g in groups for t in g})
    eg, idx = expected_goals_matrix(model, teams)
    group_idx = [[idx[t] for t in g] for g in groups]

    rng = np.random.default_rng(seed)
    nt = len(teams)
    knockout = np.zeros(nt, int)   # nådde sluttspillet (topp 32)
    r16 = np.zeros(nt, int)
    quarter = np.zeros(nt, int)
    semi = np.zeros(nt, int)
    final = np.zeros(nt, int)
    champ = np.zeros(nt, int)
    counters = {32: knockout, 16: r16, 8: quarter, 4: semi, 2: final}

    for _ in range(n):
        winners, runners, thirds = [], [], []
        for g in group_idx:
            pts = dict.fromkeys(g, 0)
            gd = dict.fromkeys(g, 0)
            gf = dict.fromkeys(g, 0)
            for a in range(4):
                for b in range(a + 1, 4):
                    i, j = g[a], g[b]
                    gi, gj = rng.poisson(eg[i, j]), rng.poisson(eg[j, i])
                    gf[i] += gi; gf[j] += gj
                    gd[i] += gi - gj; gd[j] += gj - gi
                    if gi > gj:
                        pts[i] += 3
                    elif gj > gi:
                        pts[j] += 3
                    else:
                        pts[i] += 1; pts[j] += 1
            r = sorted(g, key=lambda t: (pts[t], gd[t], gf[t], rng.random()), reverse=True)
            winners.append(r[0]); runners.append(r[1])
            thirds.append((pts[r[2]], gd[r[2]], gf[r[2]], r[2]))

        best_thirds = [t for *_, t in sorted(thirds, reverse=True)[:8]]
        bracket = list(rng.permutation(winners + runners + best_thirds))  # forenklet bracket

        while len(bracket) > 1:
            if len(bracket) in counters:
                for t in bracket:
                    counters[len(bracket)][t] += 1
            nxt = []
            for k in range(0, len(bracket), 2):
                i, j = bracket[k], bracket[k + 1]
                gi, gj = rng.poisson(eg[i, j]), rng.poisson(eg[j, i])
                if gi > gj:
                    nxt.append(i)
                elif gj > gi:
                    nxt.append(j)
                else:
                    nxt.append(i if rng.random() < 0.5 else j)  # straffer = 50/50
            bracket = nxt
        champ[bracket[0]] += 1

    return pd.DataFrame({
        "team": teams,
        "champion": champ / n,
        "final": final / n,
        "semi": semi / n,
        "quarter": quarter / n,
        "r16": r16 / n,
        "knockout": knockout / n,
    }).sort_values("champion", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    probs = simulate()
    print("Mester-sannsynlighet (topp 20):\n")
    for _, r in probs.head(20).iterrows():
        print(f"  {r.team:<22} mester {r.champion:5.1%}   "
              f"finale {r['final']:5.1%}   semi {r.semi:5.1%}")