"""Backtest: måler treffsikkerhet (log-loss) og sammenligner halveringstider."""
import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.stats import poisson

DB = "data/vm2026.duckdb"
SINCE = "2015-01-01"
CUTOFF = "2024-06-01"   # tren på alt før, test på alt etter
MIN_MATCHES = 30
MAX_GOALS = 10

def load() -> pd.DataFrame:
    con = duckdb.connect(DB, read_only=True)
    df = con.execute(f"""
        select match_date, home_team, away_team, home_score, away_score, neutral
        from fct_matches where match_date >= '{SINCE}'
    """).df()
    con.close()
    df["match_date"] = pd.to_datetime(df.match_date)
    return df

def fit(train: pd.DataFrame, half_life_years: float, ref: pd.Timestamp):
    age = (ref - train.match_date).dt.days
    w = 0.5 ** (age / (half_life_years * 365.25))
    home = pd.DataFrame({"team": train.home_team, "opponent": train.away_team,
                         "goals": train.home_score, "home_adv": (~train.neutral).astype(int),
                         "weight": w.values})
    away = pd.DataFrame({"team": train.away_team, "opponent": train.home_team,
                         "goals": train.away_score, "home_adv": 0, "weight": w.values})
    long = pd.concat([home, away], ignore_index=True)
    return smf.glm("goals ~ C(team) + C(opponent) + home_adv", data=long,
                   family=sm.families.Poisson(), freq_weights=long.weight.to_numpy()).fit()

def outcome_probs(model, home, away, neutral):
    rows = pd.DataFrame({"team": [home, away], "opponent": [away, home],
                         "home_adv": [0 if neutral else 1, 0]})
    lam, mu = model.predict(rows).to_numpy()
    m = np.outer(poisson.pmf(np.arange(MAX_GOALS + 1), lam),
                 poisson.pmf(np.arange(MAX_GOALS + 1), mu))
    return np.tril(m, -1).sum(), np.trace(m), np.triu(m, 1).sum()  # H, U, B

def log_loss(half_life_years, train, test, ref):
    model = fit(train, half_life_years, ref)
    teams = set(train.home_team) | set(train.away_team)
    losses = []
    for _, g in test.iterrows():
        if g.home_team not in teams or g.away_team not in teams:
            continue
        ph, pu, pb = outcome_probs(model, g.home_team, g.away_team, g.neutral)
        p = ph if g.home_score > g.away_score else (pu if g.home_score == g.away_score else pb)
        losses.append(-np.log(max(p, 1e-9)))
    return np.mean(losses), len(losses)

if __name__ == "__main__":
    df = load()
    train = df[df.match_date < CUTOFF]
    counts = pd.concat([train.home_team, train.away_team]).value_counts()
    keep = counts[counts >= MIN_MATCHES].index
    train = train[train.home_team.isin(keep) & train.away_team.isin(keep)]
    test = df[df.match_date >= CUTOFF]
    ref = pd.Timestamp(CUTOFF)

    print(f"Tren: {len(train)} kamper før {CUTOFF}  |  test: {len(test)} etter\n")
    print("halveringstid (år) -> log-loss (lavere = bedre)")
    for hl in [1, 2, 4, 8, 1000]:
        ll, n = log_loss(hl, train, test, ref)
        tag = "   (≈ ingen vekting / v1)" if hl == 1000 else ""
        print(f"  {hl:>4} -> {ll:.4f}   (n={n}){tag}")