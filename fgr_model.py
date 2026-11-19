"""Instanz, Kosten und Zulässigkeit der Flotten-Planung (CVRP mit Fixkosten je Fahrzeug).

Aus tourenplanung-planung/messreihe_flotte/fl_core.py und messreihe_backhaul/bh_core.py mechanisch übernommen und auf einen Fahrzeugtyp
verkürzt (Logik der Instanzbildung unverändert; die Suche steht in fgr_search.py).

Modell: ein Depot 0, Kunden 1..n, Menge d_i, eine Kapazität Q, unbegrenzt viele gleiche Fahrzeuge. Jedes genutzte Fahrzeug kostet f (Fixkosten,
in Längeneinheiten des 100 x 100-Gebiets), jede gefahrene Längeneinheit kostet 1. Gesamtkosten = f · V + D. Alle Entfernungen sind ganzzahlig
(1 Einheit = 0,1 Längeneinheit, SCALE = 10); die Fixkosten der Rechnung sind f · SCALE.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from fgr_rng import SplitMix64

SCALE = 10
DEPOTS = {"rand": (50.0, 0.0), "mitte": (50.0, 50.0)}
AREA_SIDE = 100.0
DEM_RANGE = (5, 25)                       # Mengen gleichverteilt ganzzahlig 5 bis 25


@dataclass
class Instance:
    n: int
    dem: list             # Index 0 = 0 (Depot)
    Q: int
    xy: list
    D: list               # ganzzahlige Entfernungen
    meta: dict = field(default_factory=dict)
    _nbr: dict = field(default_factory=dict)

    def neighbors(self, K=10):
        if K not in self._nbr:
            nb = [[]]
            for i in range(1, self.n + 1):
                order = sorted((j for j in range(1, self.n + 1) if j != i), key=lambda j: (self.D[i][j], j))
                nb.append(order[:K])
            self._nbr[K] = nb
        return self._nbr[K]


def dist_matrix(xy):
    n = len(xy)
    D = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = int(round(SCALE * math.hypot(xy[i][0] - xy[j][0], xy[i][1] - xy[j][1])))
            D[i][j] = D[j][i] = d
    return D


def make_base(n, depot, seed):
    """n Kunden gleichverteilt im 100 x 100-Gebiet, Mengen gleichverteilt 5..25, Depot (x, y); noch ohne Kapazität (Q = Summe der Mengen).
    Zufallsströme wie in der Messreihe (Ort: seed * 8 + 1, Menge: seed * 8 + 2)."""
    rx = SplitMix64(seed * 8 + 1)
    rd = SplitMix64(seed * 8 + 2)
    xy = [depot]
    dem = [0]
    lo, hi = DEM_RANGE
    for _ in range(n):
        u1, u2 = rx.uniform(), rx.uniform()
        xy.append((AREA_SIDE * u1, AREA_SIDE * u2))
        dem.append(lo + rd.below(hi - lo + 1))
    return Instance(n, dem, sum(dem), xy, dist_matrix(xy), dict(n=n, depot=depot, seed=seed))


def capacity(dem, k, reserve):
    """Q = max(⌈(1 + Reserve) · Σd / k⌉, größte Einzelmenge); k = Zahl der Ladungen, Reserve als Anteil (0,0 / 0,02 / 0,05 / 0,10)."""
    s = sum(dem)
    return max(int(math.ceil((1.0 + reserve) * s / k - 1e-9)), max(dem))


def with_capacity(inst, Q):
    return Instance(inst.n, inst.dem, Q, inst.xy, inst.D, inst.meta)


def make_instance(n, depot, seed, k, reserve):
    base = make_base(n, DEPOTS[depot], seed)
    return with_capacity(base, capacity(base.dem, k, reserve))


def make_custom(xy, dem, Q):
    """Handbeispiele und Tests: xy[0] ist das Depot, dem[0] = 0."""
    return Instance(len(xy) - 1, list(dem), Q, list(xy), dist_matrix(xy), {})


def depot_dist_mean(inst):
    """Mittlerer Abstand Kunde–Depot in Entfernungseinheiten."""
    return sum(inst.D[0][i] for i in range(1, inst.n + 1)) / inst.n


def lower_bound_vehicles(inst):
    """Untere Schranke der Fahrzeugzahl: ⌈Σd / Q⌉."""
    return int(math.ceil(sum(inst.dem[1:]) / inst.Q))


# ------------------------------------------------------------------------------------------------ Kosten, Zulässigkeit

def route_len(D, r):
    if not r:
        return 0
    s = D[0][r[0]] + D[r[-1]][0]
    for a, b in zip(r, r[1:]):
        s += D[a][b]
    return s


def route_load(inst, r):
    return sum(inst.dem[c] for c in r)


def distance_of(inst, routes):
    return sum(route_len(inst.D, r) for r in routes if r)


def total_cost(inst, routes, f_int):
    """Gesamtkosten = f_int · (Zahl der Fahrzeuge) + Distanz, alles in Entfernungseinheiten (f_int = f · SCALE)."""
    return sum(f_int + route_len(inst.D, r) for r in routes if r)


def verify(inst, routes):
    """Unabhängiger Prüfer: jeder Kunde genau einmal, Last <= Q, keine leere Route (Liste von Fehlern)."""
    errs = []
    seen = []
    for ri, r in enumerate(routes):
        if not r:
            errs.append(f"Tour {ri} leer")
            continue
        seen.extend(r)
        if route_load(inst, r) > inst.Q:
            errs.append(f"Tour {ri}: Last {route_load(inst, r)} > Q {inst.Q}")
    if sorted(seen) != list(range(1, inst.n + 1)):
        errs.append("Kunden nicht genau einmal")
    return errs


def savings_pure(inst):
    """Clarke-Wright (Savings) mit Kapazität Q, ohne Zufall."""
    D = inst.D
    cust = list(range(1, inst.n + 1))
    rid = {c: c for c in cust}
    rt = {c: [c] for c in cust}
    ld = {c: inst.dem[c] for c in cust}
    pairs = []
    for i in cust:
        for j in cust:
            if i < j:
                pairs.append((-(D[0][i] + D[0][j] - D[i][j]), i, j))
    pairs.sort()
    for _, i, j in pairs:
        ri, rj = rid[i], rid[j]
        if ri == rj or ld[ri] + ld[rj] > inst.Q:
            continue
        a, b = rt[ri], rt[rj]
        if a[-1] == i and b[0] == j:
            new = a + b
        elif a[0] == i and b[-1] == j:
            new = b + a
        elif a[-1] == i and b[-1] == j:
            new = a + b[::-1]
        elif a[0] == i and b[0] == j:
            new = a[::-1] + b
        else:
            continue
        rt[ri] = new
        ld[ri] += ld[rj]
        del rt[rj], ld[rj]
        for c in b:
            rid[c] = ri
    return [r[:] for r in rt.values()]
