"""Sannsynlighet for at hver spiller scorer i en gitt kamp."""
import duckdb
import numpy as np
import pandas as pd
from poisson import load_matches, filter_teams, add_weights, to_long, fit

DB = "data/vm2026.duckdb"
TOP = 6

def expected_goals(model, home, away, neutral):
    rows = pd.DataFrame({"team": [home, away], "opponent": [away, home],
                         "home_adv": [0 if neutral else 1, 0]})
    return model.predict(rows).to_numpy()  # [forventede mål hjemme, borte]

def player_shares(team, top=TOP):
    con = duckdb.connect(DB, read_only=True)
    df = con.execute(
        f"select scorer, share from player_goal_share where team = ? order by share desc limit {top}",
        [team]).df()
    con.close()
    return df

def scorer_table(model, home, away, neutral=True):
    eg = dict(zip([home, away], expected_goals(model, home, away, neutral)))
    rows = []
    for team in (home, away):
        sh = player_shares(team)
        sh["exp_goals"] = eg[team] * sh["share"]
        sh["p_score"] = 1 - np.exp(-sh["exp_goals"])
        sh["team"] = team
        rows.append(sh)
    return pd.concat(rows)

if __name__ == "__main__":
    model = fit(to_long(add_weights(filter_teams(load_matches()))))
    home, away = "Norway", "France"
    res = scorer_table(model, home, away, neutral=True)
    print(f"Scoringssannsynlighet — {home} vs {away}:\n")
    for team in (home, away):
        print(f"{team}:")
        for _, r in res[res.team == team].iterrows():
            print(f"  {r.scorer:<22} {r.p_score:5.0%}")
        print()