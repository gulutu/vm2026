"""Monte Carlo: hele VM (gruppespill + sluttspill) → mester-sannsynlighet."""
from collections import defaultdict
import numpy as np
import pandas as pd
from poisson import load_matches, filter_teams, add_weights, to_long, fit, load_fixtures

N = 5000  # antall hele turneringer (senk for raskere kjøring)

def derive_groups(fixtures):
    adj = defaultdict(set)
    for _, m in fixtures.iterrows():
        adj[m.home_team].add(m.away_team)
        adj[m.away_team].add(m.home_team)
    groups, seen = [], set()
    for t in adj:
        if t in seen:
            continue
        g = sorted({t} | adj[t]); groups.append(g); seen |= set(g)
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

if __name__ == "__main__":
    model = fit(to_long(add_weights(filter_teams(load_matches()))))
    fixtures = load_fixtures()
    groups = derive_groups(fixtures)
    teams = sorted({t for g in groups for t in g})
    eg, idx = expected_goals_matrix(model, teams)
    group_idx = [[idx[t] for t in g] for g in groups]

    rng = np.random.default_rng()
    champ = np.zeros(len(teams), int)
    final = np.zeros(len(teams), int)
    semi = np.zeros(len(teams), int)

    for _ in range(N):
        winners, runners, thirds = [], [], []
        for g in group_idx:
            pts = dict.fromkeys(g, 0); gd = dict.fromkeys(g, 0); gf = dict.fromkeys(g, 0)
            for a in range(4):
                for b in range(a + 1, 4):
                    i, j = g[a], g[b]
                    gi, gj = rng.poisson(eg[i, j]), rng.poisson(eg[j, i])
                    gf[i] += gi; gf[j] += gj; gd[i] += gi - gj; gd[j] += gj - gi
                    if gi > gj: pts[i] += 3
                    elif gj > gi: pts[j] += 3
                    else: pts[i] += 1; pts[j] += 1
            r = sorted(g, key=lambda t: (pts[t], gd[t], gf[t], rng.random()), reverse=True)
            winners.append(r[0]); runners.append(r[1])
            thirds.append((pts[r[2]], gd[r[2]], gf[r[2]], r[2]))

        best_thirds = [t for *_, t in sorted(thirds, reverse=True)[:8]]
        bracket = list(rng.permutation(winners + runners + best_thirds))  # forenklet bracket

        while len(bracket) > 1:
            if len(bracket) == 4:
                for t in bracket: semi[t] += 1
            if len(bracket) == 2:
                for t in bracket: final[t] += 1
            nxt = []
            for k in range(0, len(bracket), 2):
                i, j = bracket[k], bracket[k + 1]
                gi, gj = rng.poisson(eg[i, j]), rng.poisson(eg[j, i])
                if gi > gj: nxt.append(i)
                elif gj > gi: nxt.append(j)
                else: nxt.append(i if rng.random() < 0.5 else j)  # straffer = 50/50
            bracket = nxt
        champ[bracket[0]] += 1

    rev = {i: t for t, i in idx.items()}
    print(f"Mester-sannsynlighet ({N:,} simulerte turneringer):\n")
    for i in np.argsort(-champ)[:20]:
        print(f"  {rev[i]:<22} mester {champ[i]/N:5.1%}   "
              f"finale {final[i]/N:5.1%}   semi {semi[i]/N:5.1%}")