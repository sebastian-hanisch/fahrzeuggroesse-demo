"""Orakel-Tests (DEMO-PLAYBOOK §12): Kern gegen unabhängige Rechenwege.

  1. Das exakte Verfahren der Demo (Held-Karp je Kundenmenge plus Partitions-DP) gegen eine Vollaufzählung: alle Reihenfolgen der Kunden, je Reihenfolge die
     beste Zerlegung in aufeinanderfolgende Touren (Split-DP). Anderer Rechenweg, n <= 7.
  2. Dasselbe exakte Verfahren gegen ein CP-SAT-Modell (Mehrfach-Kreis mit Kapazität und Fixkosten), n = 9.
  3. Die eigene Suche gegen das exakte Verfahren (n = 7, 9, 12): nie darunter, mittlere Lücke als Band; bei n = 12 und Reserve 0 % ist die Lücke
     schwächer und wird als Band ausgewiesen, nicht versteckt.
  4. OR-Tools mit Fixkosten: zulässig und nicht besser als das Optimum.
  5. Anpassung von a und b gegen numpy (gewichtete kleinste Quadrate).
"""

import itertools
import math

import numpy as np
import pytest

import fgr_formula as FO
import fgr_model as M
import fgr_search as S
import fgr_solvers as V


def brute_force(inst, f_int):
    """Vollaufzählung: jede Reihenfolge der Kunden als ein großer Rundweg, optimal zerlegt in aufeinanderfolgende Touren mit Last <= Q."""
    n, D, dem, Q = inst.n, inst.D, inst.dem, inst.Q
    best = math.inf
    for perm in itertools.permutations(range(1, n + 1)):
        # dp[i] = beste Kosten, die ersten i Kunden der Reihenfolge zu bedienen
        dp = [math.inf] * (n + 1)
        dp[0] = 0
        for i in range(n):
            load = 0
            for j in range(i, n):
                load += dem[perm[j]]
                if load > Q:
                    break
                length = D[0][perm[i]] + sum(D[perm[t]][perm[t + 1]] for t in range(i, j)) + D[perm[j]][0]
                if dp[i] + length + f_int < dp[j + 1]:
                    dp[j + 1] = dp[i] + length + f_int
        best = min(best, dp[n])
    return best


def cp_sat(inst, f_int):
    """CP-SAT-Modell: Mehrfach-Kreis über die Knoten, Lastvariablen je Knoten, Fixkosten je Bogen aus dem Depot."""
    from ortools.sat.python import cp_model
    n, D, dem, Q = inst.n, inst.D, inst.dem, inst.Q
    m = cp_model.CpModel()
    arcs, lits = [], {}
    for i in range(n + 1):
        for j in range(n + 1):
            if i != j:
                lit = m.NewBoolVar(f"x{i}_{j}")
                lits[(i, j)] = lit
                arcs.append((i, j, lit))
    m.AddMultipleCircuit(arcs)
    load = [m.NewIntVar(dem[i], Q, f"u{i}") for i in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            if i != j:
                m.Add(load[j] >= load[i] + dem[j]).OnlyEnforceIf(lits[(i, j)])
    m.Minimize(sum(D[i][j] * lit for (i, j), lit in lits.items()) + f_int * sum(lits[(0, j)] for j in range(1, n + 1)))
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = 60
    s.parameters.num_workers = 1
    s.parameters.random_seed = 1
    status = s.Solve(m)
    assert status == cp_model.OPTIMAL
    return round(s.ObjectiveValue())


CASES_SMALL = [(6, "rand", 11, 2, 0.0), (6, "mitte", 12, 3, 0.0), (7, "rand", 13, 2, 0.1), (7, "mitte", 14, 3, 0.0), (7, "rand", 15, 2, 0.0)]


@pytest.mark.parametrize("n,depot,seed,k,s", CASES_SMALL)
@pytest.mark.parametrize("f", [0, 50, 400])
def test_exaktes_verfahren_gleich_vollaufzaehlung(n, depot, seed, k, s, f):
    inst = M.make_instance(n, depot, seed, k, s)
    assert V.exact_optima(inst, [f * M.SCALE])[f * M.SCALE] == brute_force(inst, f * M.SCALE)


def test_exaktes_verfahren_gleich_cp_sat_bei_neun_kunden():
    pytest.importorskip("ortools")
    for seed, k, s in ((21, 3, 0.0), (23, 3, 0.1)):
        inst = M.make_instance(9, "rand", seed, k, s)
        for f in (0, 100):
            assert V.exact_optima(inst, [f * M.SCALE])[f * M.SCALE] == cp_sat(inst, f * M.SCALE), (seed, f)


def test_exaktes_verfahren_gerade_von_hand(gerade):
    assert V.exact_optima(gerade, [0, 1000]) == {0: 800, 1000: 2800}


def test_suche_nie_unter_dem_optimum_und_lueckenband_bei_n_7_und_9():
    gaps = []
    for n, seeds in ((7, range(30, 36)), (9, range(40, 44))):
        for seed in seeds:
            for k, s in ((2, 0.0), (3, 0.0)):
                inst = M.make_instance(n, "rand" if seed % 2 else "mitte", seed, k, s)
                for f in (0, 100):
                    opt = V.exact_optima(inst, [f * M.SCALE])[f * M.SCALE]
                    routes = S.solve_fix(inst, f * M.SCALE, 80, seed)
                    assert M.verify(inst, routes) == []
                    val = M.total_cost(inst, routes, f * M.SCALE)
                    assert val >= opt                                                  # nie besser als das Optimum
                    gaps.append(100.0 * (val - opt) / opt)
    assert sum(gaps) / len(gaps) <= 0.3                                                # Band: gemessen weit darunter
    assert sum(1 for g in gaps if g <= 1e-9) >= 0.8 * len(gaps)                        # in den meisten Fällen genau das Optimum


def test_suche_bei_12_kunden_und_knapper_kapazitaet_als_band():
    """Bei Reserve 0 % ist die Suche am schwächsten (Kernfrage 2 der App); hier ein Band, kein Beleg für n = 20 und 40."""
    gaps = []
    for seed in range(2000, 2004):
        inst = M.make_instance(12, "rand" if seed % 2 else "mitte", seed, 3, 0.0)
        f_ints = [f * M.SCALE for f in (0, 100, 400)]
        opts = V.exact_optima(inst, f_ints)
        sols = S.short_chain(inst, (0, 100, 400), 120, seed)
        for f in (0, 100, 400):
            val = M.total_cost(inst, sols[f], f * M.SCALE)
            assert val >= opts[f * M.SCALE]
            gaps.append(100.0 * (val - opts[f * M.SCALE]) / opts[f * M.SCALE])
    assert sum(gaps) / len(gaps) <= 1.5


def test_ortools_mit_fixkosten_ist_zulaessig_und_nicht_besser_als_das_optimum():
    pytest.importorskip("ortools")
    inst = M.make_instance(9, "rand", 40, 3, 0.0)
    for setting in V.SETTINGS:
        routes, _obj = V.solve_ortools(inst, 100 * M.SCALE, 1, setting)
        assert routes is not None and M.verify(inst, routes) == []
        assert M.total_cost(inst, routes, 100 * M.SCALE) >= V.exact_optima(inst, [100 * M.SCALE])[100 * M.SCALE]


def test_anpassung_von_a_und_b_gleich_numpy_kleinste_quadrate():
    rng = np.random.default_rng(5)
    rows = []
    for _ in range(30):
        x1, x2 = rng.uniform(1000, 9000), rng.uniform(2000, 6000)
        rows.append((0.9 * x1 + 0.6 * x2 + rng.normal(0, 150), x1, x2))
    a, b = FO.fit_ab(rows)
    D = np.array([r[0] for r in rows])
    X = np.array([[r[1], r[2]] for r in rows])
    w = 1.0 / D                                                                        # Gewicht 1 / D² in den Quadraten = Zeilen mit 1 / D skalieren
    coef, *_ = np.linalg.lstsq(X * w[:, None], D * w, rcond=None)
    assert a == pytest.approx(coef[0], rel=1e-9) and b == pytest.approx(coef[1], rel=1e-9)


def test_formel_von_hand():
    """Depot (0, 0), vier Kunden mit Menge 5 im Abstand 10, 20, 30, 40 Längeneinheiten: Mittel 25 Längeneinheiten = 250 Einheiten, Summe der Mengen 20, Q = 10, n = 4, A = 1 000 000 Einheiten²."""
    inst = M.make_custom([(0.0, 0.0), (10.0, 0.0), (20.0, 0.0), (30.0, 0.0), (40.0, 0.0)], [0, 5, 5, 5, 5], 10)
    assert M.depot_dist_mean(inst) == 250
    want = 1.0 * 2 * 250 * 20 / 10 + 0.5 * math.sqrt(4 * 1_000_000)                    # = 1000 + 1000
    assert FO.predicted_distance(inst, 10, 1.0, 0.5) == pytest.approx(want) == pytest.approx(2000.0)
    assert FO.predicted_vehicles(inst, 10) == 2 and FO.predicted_vehicles(inst, 7) == 3
