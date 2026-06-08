"""v1: Poisson-styrkemodell + kampprediksjoner."""
import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.stats import poisson

DB = "data/vm2026.duckdb"
SINCE = "2015-01-01"
MIN_MATCHES = 30
MAX_GOALS = 10

def load_matches() -> pd.DataFrame:
    con = duckdb.connect(DB, read_only=True)
    df = con.execute(f"""
        select home_team, away_team, home_score, away_score, neutral
        from fct_matches where match_date >= '{SINCE}'
    """).df()
    con.close()
    return df

def load_fixtures() -> pd.DataFrame:
    con = duckdb.connect(DB, read_only=True)
    df = con.execute("""
        select match_date, home_team, away_team, neutral
        from fct_fixtures order by match_date
    """).df()
    con.close()
    return df

def filter_teams(df: pd.DataFrame) -> pd.DataFrame:
    counts = pd.concat([df.home_team, df.away_team]).value_counts()
    keep = counts[counts >= MIN_MATCHES].index
    return df[df.home_team.isin(keep) & df.away_team.isin(keep)]

def to_long(df: pd.DataFrame) -> pd.DataFrame:
    home = pd.DataFrame({"team": df.home_team, "opponent": df.away_team,
                         "goals": df.home_score, "home_adv": (~df.neutral).astype(int)})
    away = pd.DataFrame({"team": df.away_team, "opponent": df.home_team,
                         "goals": df.away_score, "home_adv": 0})
    return pd.concat([home, away], ignore_index=True)

def fit(long: pd.DataFrame):
    return smf.glm("goals ~ C(team) + C(opponent) + home_adv",
                   data=long, family=sm.families.Poisson()).fit()

def predict_match(model, home, away, neutral=True):
    rows = pd.DataFrame({
        "team": [home, away],
        "opponent": [away, home],
        "home_adv": [0 if neutral else 1, 0],
    })
    lam, mu = model.predict(rows).to_numpy()
    h = poisson.pmf(np.arange(MAX_GOALS + 1), lam)
    a = poisson.pmf(np.arange(MAX_GOALS + 1), mu)
    matrix = np.outer(h, a)                       # P(hjemmemål=i, bortemål=j)
    i, j = np.unravel_index(matrix.argmax(), matrix.shape)
    return {
        "exp_home": lam, "exp_away": mu,
        "p_home": np.tril(matrix, -1).sum(),      # i > j
        "p_draw": np.trace(matrix),               # i == j
        "p_away": np.triu(matrix, 1).sum(),       # i < j
        "score": (i, j),
    }

if __name__ == "__main__":
    model = fit(to_long(filter_teams(load_matches())))
    fixtures = load_fixtures()

    print("Norges gruppespill (Gruppe I):\n")
    norway = fixtures[(fixtures.home_team == "Norway") | (fixtures.away_team == "Norway")]
    for _, m in norway.iterrows():
        p = predict_match(model, m.home_team, m.away_team, m.neutral)
        print(f"{m.home_team} – {m.away_team}")
        print(f"  Forventet: {p['exp_home']:.1f}–{p['exp_away']:.1f}   "
              f"H {p['p_home']:.0%}  U {p['p_draw']:.0%}  B {p['p_away']:.0%}\n")