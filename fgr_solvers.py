"""Vergleichslöser und exaktes Verfahren für kleine Instanzen.

  solve_ortools(inst, f_int, seconds, setting)   OR-Tools Routing mit Fixkosten je Fahrzeug (SetFixedCostOfAllVehicles), Guided Local Search
  exact_optimum(inst, f_int)                     Held-Karp je Kundenmenge plus Partitions-DP, exakt für n <= 12

Aus tourenplanung-planung/messreihe_flotte/fl_core.py übernommen und auf einen Fahrzeugtyp verkürzt."""
from __future__ import annotations

import math


SETTINGS = ("standard", "sav")
SETTING_LABELS = {"standard": "Standard (PATH_CHEAPEST_ARC)", "sav": "SAVINGS"}
EXACT_N_MAX = 12


def solve_ortools(inst, f_int, seconds, setting="standard", nveh=None):
    """Ein Fahrzeugtyp, Fixkosten f_int je genutztes Fahrzeug, Zielwert Distanz + Fixkosten. Einstellung 'standard': PATH_CHEAPEST_ARC + Guided
    Local Search; 'sav': SAVINGS + Guided Local Search. Rückgabe (Routen, Zielwert) oder (None, None)."""
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2 as e
    D, n, Q = inst.D, inst.n, inst.Q
    if nveh is None:
        nveh = min(n, int(math.ceil(sum(inst.dem) / Q)) + 4)
    mgr = pywrapcp.RoutingIndexManager(n + 1, nveh, 0)
    routing = pywrapcp.RoutingModel(mgr)

    def dist_cb(i, j):
        return D[mgr.IndexToNode(i)][mgr.IndexToNode(j)]

    ti = routing.RegisterTransitCallback(dist_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(ti)
    routing.SetFixedCostOfAllVehicles(int(f_int))

    def dem_cb(i):
        return inst.dem[mgr.IndexToNode(i)]

    di = routing.RegisterUnaryTransitCallback(dem_cb)
    routing.AddDimensionWithVehicleCapacity(di, 0, [Q] * nveh, True, "cap")
    p = pywrapcp.DefaultRoutingSearchParameters()
    p.first_solution_strategy = (e.FirstSolutionStrategy.PATH_CHEAPEST_ARC if setting == "standard" else e.FirstSolutionStrategy.SAVINGS)
    p.local_search_metaheuristic = e.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    p.time_limit.seconds = int(seconds)
    p.log_search = False
    sol = routing.SolveWithParameters(p)
    if sol is None:
        return None, None
    routes = []
    for v in range(nveh):
        idx = routing.Start(v)
        r = []
        while not routing.IsEnd(idx):
            node = mgr.IndexToNode(idx)
            if node != 0:
                r.append(node)
            idx = sol.Value(routing.NextVar(idx))
        if r:
            routes.append(r)
    return routes, sol.ObjectiveValue()


def exact_optima(inst, f_ints):
    """Exakte Zielwerte (Distanz + f_int je Fahrzeug) für n <= 12 und mehrere Fixkosten zugleich: kürzeste Rundtour je Kundenmenge (Held-Karp,
    einmal), dann je f_int die beste Zerlegung in Mengen mit Last <= Q (Partitions-DP über alle Teilmengen). Rückgabe {f_int: Zielwert}."""
    n, D, dem, Q = inst.n, inst.D, inst.dem, inst.Q
    if n > EXACT_N_MAX:
        raise ValueError(f"exakt nur bis n = {EXACT_N_MAX}")
    full = (1 << n) - 1
    INF = float("inf")
    dp = [[INF] * n for _ in range(1 << n)]
    for j in range(n):
        dp[1 << j][j] = D[0][j + 1]
    for S in range(1, 1 << n):
        for j in range(n):
            if not (S >> j) & 1 or dp[S][j] == INF:
                continue
            base = dp[S][j]
            for k in range(n):
                if (S >> k) & 1:
                    continue
                T = S | (1 << k)
                v = base + D[j + 1][k + 1]
                if v < dp[T][k]:
                    dp[T][k] = v
    load = [0] * (1 << n)
    for S in range(1, 1 << n):
        low = (S & -S).bit_length() - 1
        load[S] = load[S & (S - 1)] + dem[low + 1]
    tour = [INF] * (1 << n)
    for S in range(1, 1 << n):
        if load[S] > Q:
            continue
        best = INF
        for j in range(n):
            if (S >> j) & 1:
                v = dp[S][j] + D[j + 1][0]
                if v < best:
                    best = v
        tour[S] = best
    out = {}
    for f_int in f_ints:
        best = [INF] * (1 << n)
        best[0] = 0
        for S in range(1, 1 << n):
            low = S & -S
            T = S
            while T:
                if T & low and tour[T] < INF:
                    v = tour[T] + f_int + best[S ^ T]
                    if v < best[S]:
                        best[S] = v
                T = (T - 1) & S
        out[f_int] = best[full]
    return out


def exact_optimum(inst, f_int):
    """Exakter Zielwert für ein f_int (siehe exact_optima)."""
    return exact_optima(inst, [f_int])[f_int]
