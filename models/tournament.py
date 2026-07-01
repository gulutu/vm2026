"""Importerbar turneringssimulering: sannsynlighet per lag for hver runde.

Henter de 12 gruppene (med bokstav A–L) fra kampoppsettet, bruker faktiske
resultater for spilte gruppekamper, og trekker bare de gjenstående tilfeldig.
Sluttspillet følger den EKTE FIFA-bracketen (faste slot-koder 1A/2B/3.-plass +
W/L-treet), ikke en tilfeldig trekning.

Kjør direkte for en rask kontroll:  uv run python models/tournament.py
Ellers: importer simulate() fra appen.
"""
import re
import unicodedata

import duckdb
import numpy as np
import pandas as pd

from poisson import load_matches, filter_teams, add_weights, to_long, fit

DB = "data/vm2026.duckdb"
N_DEFAULT = 5000

# Gruppespillet spilles 11.–27. juni 2026; vinduet plukker ut nøyaktig de 72
# gruppekampene (spilte + kommende) og holder sluttspillkamper ute.
GROUP_FROM = "2026-06-11"
GROUP_TO = "2026-06-27"

# ── Den ekte sluttspill-strukturen (fast for VM 2026) ──────────────────────
# Round of 32: (kampnr, plass A, plass B). Plass = ("win"|"run", gruppebokstav)
# eller ("third", sett av tillatte grupper). Tredjeplass er alltid plass B.
WIN, RUN, THIRD = "win", "run", "third"
R32 = [
    (73, (RUN, "A"), (RUN, "B")),
    (74, (WIN, "E"), (THIRD, frozenset("ABCDF"))),
    (75, (WIN, "F"), (RUN, "C")),
    (76, (WIN, "C"), (RUN, "F")),
    (77, (WIN, "I"), (THIRD, frozenset("CDFGH"))),
    (78, (RUN, "E"), (RUN, "I")),
    (79, (WIN, "A"), (THIRD, frozenset("CEFHI"))),
    (80, (WIN, "L"), (THIRD, frozenset("EHIJK"))),
    (81, (WIN, "D"), (THIRD, frozenset("BEFIJ"))),
    (82, (WIN, "G"), (THIRD, frozenset("AEHIJ"))),
    (83, (RUN, "K"), (RUN, "L")),
    (84, (WIN, "H"), (RUN, "J")),
    (85, (WIN, "B"), (THIRD, frozenset("EFGIJ"))),
    (86, (WIN, "J"), (RUN, "H")),
    (87, (WIN, "K"), (THIRD, frozenset("DEIJL"))),
    (88, (RUN, "D"), (RUN, "G")),
]
# Resten av treet: (kampnr, vinner av X, vinner av Y). Hopper over bronsefinalen.
TREE = [
    (89, 74, 77), (90, 73, 75), (91, 76, 78), (92, 79, 80),
    (93, 83, 84), (94, 81, 82), (95, 86, 88), (96, 85, 87),
    (97, 89, 90), (98, 93, 94), (99, 91, 92), (100, 95, 96),
    (101, 97, 98), (102, 99, 100),
    (104, 101, 102),
]
THIRD_SLOTS = [(num, b[1]) for num, a, b in R32 if b[0] == THIRD]

# Barn i sluttspilltreet: hvilken senere kamp mottar vinneren av denne kampen.
_KO_CHILD = {}
for _num, _fa, _fb in TREE:
    _KO_CHILD[_fa] = _num
    _KO_CHILD[_fb] = _num
_ALL_KO_NUMS = [n for n, _, _ in R32] + [n for n, _, _ in TREE]

# Bro mellom openfootball-navn (raw_schedule) og martj42-navn (modellen).
_ALIAS = {"usa": "united states"}


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = s.lower().replace("&", " and ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


def load_group_matches():
    """Alle gruppekamper (spilte har resultat, kommende har NULL), martj42-navn."""
    con = duckdb.connect(DB, read_only=True)
    df = con.execute(
        f"""
        select home_team, away_team, home_score, away_score
        from raw_results
        where tournament = 'FIFA World Cup'
          and date between '{GROUP_FROM}' and '{GROUP_TO}'
        """
    ).df()
    con.close()
    return df


def load_group_letters():
    """{bokstav: sett av lagnavn (openfootball)} fra kampoppsettet."""
    con = duckdb.connect(DB, read_only=True)
    df = con.execute(
        "select grp, team1, team2 from raw_schedule where grp is not null"
    ).df()
    con.close()
    letters = {}
    for r in df.itertuples():
        L = str(r.grp).replace("Group ", "").strip()
        letters.setdefault(L, set()).update([r.team1, r.team2])
    return letters


def load_knockout_schedule():
    """{kampnr: (lag1, lag2)} for sluttspillkamper, openfootball-navn.
    Etter hvert som kamper spilles bytter openfootball ut plassholdere
    ("W74"/"L74") med det ekte laget i senere runders rader."""
    con = duckdb.connect(DB, read_only=True)
    df = con.execute(
        "select num, team1, team2 from raw_schedule "
        "where num is not null and round != 'Match for third place'"
    ).df()
    con.close()
    return {int(r.num): (r.team1, r.team2) for r in df.itertuples()}


def resolve_played_knockout(byteam, to_mart, idx):
    """{kampnr: lagindeks} for sluttspillkamper som allerede er avgjort — vinneren
    leses av at neste kamps rad har byttet ut W##/L## med et ekte lagnavn."""
    played = {}
    for num in _ALL_KO_NUMS:
        child = _KO_CHILD.get(num)
        if child is None or child not in byteam:
            continue
        t1, t2 = byteam[num]
        cset = set(byteam[child])
        winner = t1 if t1 in cset else (t2 if t2 in cset else None)
        if winner is not None:
            played[num] = idx[to_mart(winner)]
    return played


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


def _ko_winner(i, j, eg, rng):
    """Spill én cup-kamp; uavgjort avgjøres 50/50 (straffer)."""
    gi, gj = rng.poisson(eg[i, j]), rng.poisson(eg[j, i])
    if gi > gj:
        return i
    if gj > gi:
        return j
    return i if rng.random() < 0.5 else j


def _play_group(g_idx, played, eg, rng):
    """Spill en gruppe; returner rangering (vinner, toer, treer, …)."""
    pts = dict.fromkeys(g_idx, 0)
    gd = dict.fromkeys(g_idx, 0)
    gf = dict.fromkeys(g_idx, 0)
    for a in range(len(g_idx)):
        for b in range(a + 1, len(g_idx)):
            i, j = g_idx[a], g_idx[b]
            res = played.get(frozenset((i, j)))
            if res is not None:
                hi, hs, as_ = res
                gi, gj = (hs, as_) if hi == i else (as_, hs)
            else:
                gi, gj = rng.poisson(eg[i, j]), rng.poisson(eg[j, i])
            gf[i] += gi; gf[j] += gj
            gd[i] += gi - gj; gd[j] += gj - gi
            if gi > gj:
                pts[i] += 3
            elif gj > gi:
                pts[j] += 3
            else:
                pts[i] += 1; pts[j] += 1
    rank = sorted(g_idx, key=lambda t: (pts[t], gd[t], gf[t], rng.random()),
                  reverse=True)
    return rank, pts, gd, gf


def _match_thirds(qual_letters, rng):
    """Koble de 8 kvalifiserte treerne til tredjeplass-plassene innenfor de
    tillatte settene (Kuhns algoritme → gyldig kobling)."""
    slots = list(THIRD_SLOTS)
    rng.shuffle(slots)
    slot_letter = {}

    def assign(letter, seen):
        for sid, allowed in slots:
            if letter in allowed and sid not in seen:
                seen.add(sid)
                if sid not in slot_letter or assign(slot_letter[sid], seen):
                    slot_letter[sid] = letter
                    return True
        return False

    for L in qual_letters:
        assign(L, set())
    # Reserveløsning hvis en perfekt kobling ikke ble funnet (skal ikke skje).
    if len(slot_letter) < len(slots):
        rest_L = [L for L in qual_letters if L not in slot_letter.values()]
        rest_S = [sid for sid, _ in slots if sid not in slot_letter]
        for sid, L in zip(rest_S, rest_L):
            slot_letter[sid] = L
    return slot_letter


def simulate(model=None, n=N_DEFAULT, seed=None):
    """Simulerer hele VM n ganger via den ekte bracketen. Returnerer DataFrame
    med sannsynlighet per lag for hver runde, sortert på mester-sannsynlighet.
    Spilte gruppe- og sluttspillkamper er låst til sitt faktiske resultat."""
    if model is None:
        model = fit(to_long(add_weights(filter_teams(load_matches()))))

    gm = load_group_matches()
    teams = sorted(set(gm.home_team) | set(gm.away_team))
    eg, idx = expected_goals_matrix(model, teams)

    # Gruppene med bokstav, oversatt fra openfootball- til martj42-navn.
    mart = {_norm(t): t for t in teams}

    def to_mart(name):
        k = _ALIAS.get(_norm(name), _norm(name))
        if k not in mart:
            raise ValueError(f"Fant ikke martj42-navn for '{name}' (norm '{k}')")
        return mart[k]

    groups_by_letter = {}
    for L, off_teams in load_group_letters().items():
        groups_by_letter[L] = [idx[to_mart(t)] for t in sorted(off_teams)]
    assert len(groups_by_letter) == 12 and all(
        len(v) == 4 for v in groups_by_letter.values()), "Gruppene ble ikke 12×4"

    # Faktiske resultater, nøklet på uordnet lag-par (i hjemmelagets retning).
    played = {}
    for _, m in gm.iterrows():
        if (pd.notna(m.home_score) and pd.notna(m.away_score)
                and m.home_team in idx and m.away_team in idx):
            i, j = idx[m.home_team], idx[m.away_team]
            played[frozenset((i, j))] = (i, int(m.home_score), int(m.away_score))

    played_ko = resolve_played_knockout(load_knockout_schedule(), to_mart, idx)

    rng = np.random.default_rng(seed)
    nt = len(teams)
    knockout = np.zeros(nt, int)
    r16 = np.zeros(nt, int)
    quarter = np.zeros(nt, int)
    semi = np.zeros(nt, int)
    final = np.zeros(nt, int)
    champ = np.zeros(nt, int)

    def slot_team(slot, num, win, run, third, s2l):
        if slot[0] == WIN:
            return win[slot[1]]
        if slot[0] == RUN:
            return run[slot[1]]
        return third[s2l[num]]

    for _ in range(n):
        win, run, third = {}, {}, {}
        third_rank = []
        for L, g_idx in groups_by_letter.items():
            rank, pts, gd, gf = _play_group(g_idx, played, eg, rng)
            win[L], run[L], third[L] = rank[0], rank[1], rank[2]
            t = rank[2]
            third_rank.append((pts[t], gd[t], gf[t], rng.random(), L))

        third_rank.sort(reverse=True)
        qual_letters = [x[4] for x in third_rank[:8]]
        s2l = _match_thirds(qual_letters, rng)

        res = {}
        r32_teams = []
        for num, sa, sb in R32:
            i = slot_team(sa, num, win, run, third, s2l)
            j = slot_team(sb, num, win, run, third, s2l)
            r32_teams += [i, j]
            res[num] = played_ko[num] if num in played_ko else _ko_winner(i, j, eg, rng)
        for num, fa, fb in TREE:
            res[num] = (played_ko[num] if num in played_ko
                        else _ko_winner(res[fa], res[fb], eg, rng))

        for t in r32_teams:
            knockout[t] += 1
        for num in range(73, 89):
            r16[res[num]] += 1
        for num in range(89, 97):
            quarter[res[num]] += 1
        for num in range(97, 101):
            semi[res[num]] += 1
        for num in (101, 102):
            final[res[num]] += 1
        champ[res[104]] += 1

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