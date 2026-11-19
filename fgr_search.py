"""Eigene Suche für das CVRP mit Fixkosten je Fahrzeug: Ruin-and-Recreate mit Relocate, Swap, 2-opt, 2-opt*, Verschmelzen; Packungsstart.

Aus tourenplanung-planung/messreihe_flotte/fl_core.py übernommen und auf einen Fahrzeugtyp verkürzt. EINE Änderung gegenüber der Messreihe:
Der Packungsstart (Behälter-Zuordnung auf ⌈Σd / Q⌉ Fahrzeuge) ist kein CP-SAT-Lauf mehr, sondern eine eigene Tiefensuche mit fester Knotengrenze
(`pack_bins`). Grund: CP-SAT fand auf Windows und Linux verschiedene Packungen (Restmessung AP 0 e: 11 von 12 Zeilen gleich, die Diagnose lief nur an der einen abweichenden Zeile). Die Tiefensuche
rechnet nur mit Ganzzahlen und hängt nicht von der Plattform ab; ein Neuvergleich der zwölf Zeilen aus AP 0 zwischen Windows und Linux wurde nicht gerechnet, belegt ist der Docker-Lauf der Tests.

Kosten einer Route: Länge + Fixkosten (f_int = f · SCALE); eine leere Route kostet nichts.
"""
from __future__ import annotations


import fgr_model as M
from fgr_rng import SplitMix64

EPS = 1e-9
PACK_NODES = 200_000                      # Knotengrenze der Packungssuche (deterministisch, keine Zeit)


def _make_rc(f_int):
    def rc(length, load):
        return 0 if load <= 0 else length + f_int

    return rc


class St:
    def __init__(self, inst, routes, rc):
        self.inst, self.rc, self.qmax = inst, rc, inst.Q
        self.routes = [r[:] for r in routes if r]
        self.load, self.len, self.where = [], [], {}
        for ri in range(len(self.routes)):
            self.load.append(0)
            self.len.append(0)
            self.refresh(ri)

    def refresh(self, ri):
        inst = self.inst
        r = self.routes[ri]
        self.load[ri] = sum(inst.dem[c] for c in r)
        self.len[ri] = M.route_len(inst.D, r)
        for idx, c in enumerate(r):
            self.where[c] = (ri, idx)

    def add_route(self):
        self.routes.append([])
        self.load.append(0)
        self.len.append(0)
        return len(self.routes) - 1

    def compact(self):
        keep = [r for r in self.routes if r]
        self.__init__(self.inst, keep, self.rc)

    def cost(self):
        return sum(self.rc(self.len[i], self.load[i]) for i in range(len(self.routes)) if self.routes[i])


def _ins_cost(D, r, q, c):
    p = r[q - 1] if q > 0 else 0
    nx = r[q] if q < len(r) else 0
    return D[p][c] + D[c][nx] - D[p][nx]


def _rem_gain(D, r, idx):
    c = r[idx]
    p = r[idx - 1] if idx > 0 else 0
    nx = r[idx + 1] if idx + 1 < len(r) else 0
    return D[p][c] + D[c][nx] - D[p][nx]


def _local_search(st):
    inst, D, rc, qmax = st.inst, st.inst.D, st.rc, st.qmax
    nbr = inst.neighbors(10)
    custs = list(range(1, inst.n + 1))
    improved = True
    guard = 0
    while improved and guard < 200:
        guard += 1
        improved = False
        # --- Relocate
        for c in custs:
            ri, idx = st.where[c]
            r = st.routes[ri]
            d = inst.dem[c]
            gain = _rem_gain(D, r, idx)
            cost_i = rc(st.len[ri], st.load[ri])
            cost_i_new = rc(st.len[ri] - gain, st.load[ri] - d)
            best = None
            for v in nbr[c]:
                rj, jdx = st.where[v]
                if rj == ri:
                    tmp = r[:idx] + r[idx + 1:]
                    pv = jdx if jdx < idx else jdx - 1
                    for q in (pv, pv + 1):
                        if q == idx:
                            continue
                        delta = rc(st.len[ri] - gain + _ins_cost(D, tmp, q, c), st.load[ri]) - cost_i
                        if delta < -EPS and (best is None or delta < best[0]):
                            best = (delta, rj, q)
                else:
                    if st.load[rj] + d > qmax:
                        continue
                    rv = st.routes[rj]
                    cost_j = rc(st.len[rj], st.load[rj])
                    for q in (jdx, jdx + 1):
                        delta = (rc(st.len[rj] + _ins_cost(D, rv, q, c), st.load[rj] + d) - cost_j) + (cost_i_new - cost_i)
                        if delta < -EPS and (best is None or delta < best[0]):
                            best = (delta, rj, q)
            if len(r) > 1:
                delta = rc(2 * D[0][c], d) + (cost_i_new - cost_i)
                if delta < -EPS and (best is None or delta < best[0]):
                    best = (delta, -1, 0)
            if best is not None:
                _, rj, q = best
                del r[idx]
                if rj == ri:
                    st.routes[ri].insert(q, c)
                    st.refresh(ri)
                elif rj == -1:
                    nr = st.add_route()
                    st.routes[nr].append(c)
                    st.refresh(nr)
                    st.refresh(ri)
                else:
                    st.routes[rj].insert(q, c)
                    st.refresh(ri)
                    st.refresh(rj)
                improved = True
                if not st.routes[ri]:
                    st.compact()    # leere Route entfernen
                    break
        # --- Swap
        for c in custs:
            for v in nbr[c]:
                ri, idx = st.where[c]
                rj, jdx = st.where[v]
                if rj == ri:
                    continue
                r, rv = st.routes[ri], st.routes[rj]
                dc, dv = inst.dem[c], inst.dem[v]
                nli, nlj = st.load[ri] - dc + dv, st.load[rj] - dv + dc
                if nli > qmax or nlj > qmax:
                    continue
                p1 = r[idx - 1] if idx > 0 else 0
                n1 = r[idx + 1] if idx + 1 < len(r) else 0
                p2 = rv[jdx - 1] if jdx > 0 else 0
                n2 = rv[jdx + 1] if jdx + 1 < len(rv) else 0
                di = D[p1][v] + D[v][n1] - D[p1][c] - D[c][n1]
                dj = D[p2][c] + D[c][n2] - D[p2][v] - D[v][n2]
                delta = rc(st.len[ri] + di, nli) + rc(st.len[rj] + dj, nlj) - rc(st.len[ri], st.load[ri]) - rc(st.len[rj], st.load[rj])
                if delta < -EPS:
                    r[idx], rv[jdx] = v, c
                    st.refresh(ri)
                    st.refresh(rj)
                    improved = True
                    break
        # --- 2-opt innerhalb einer Route
        for ri in range(len(st.routes)):
            r = st.routes[ri]
            if len(r) < 2:
                continue
            changed = True
            while changed:
                changed = False
                for i in range(len(r) - 1):
                    a = r[i - 1] if i > 0 else 0
                    for j in range(i + 1, len(r)):
                        b = r[j + 1] if j + 1 < len(r) else 0
                        delta = D[a][r[j]] + D[r[i]][b] - D[a][r[i]] - D[r[j]][b]
                        if delta < 0:
                            r[i:j + 1] = r[i:j + 1][::-1]
                            changed = improved = True
                            break
                    if changed:
                        break
            st.refresh(ri)
        # --- 2-opt* (Endstücke tauschen)
        for c in custs:
            for v in nbr[c]:
                ri, idx = st.where[c]
                rj, jdx = st.where[v]
                if ri == rj:
                    continue
                r1, r2 = st.routes[ri], st.routes[rj]
                a, b = idx + 1, jdx
                p1, s1, p2, s2 = r1[:a], r1[a:], r2[:b], r2[b:]
                n1 = p1 + s2
                n2 = p2 + s1
                l1 = sum(inst.dem[x] for x in n1)
                l2 = sum(inst.dem[x] for x in n2)
                if l1 > qmax or l2 > qmax:
                    continue
                len1 = M.route_len(D, n1)
                len2 = M.route_len(D, n2)
                delta = rc(len1, l1) + rc(len2, l2) - rc(st.len[ri], st.load[ri]) - rc(st.len[rj], st.load[rj])
                if delta < -EPS:
                    st.routes[ri], st.routes[rj] = n1, n2
                    st.refresh(ri)
                    st.refresh(rj)
                    if not n1 or not n2:
                        st.compact()
                    improved = True
                    break
        # --- Verschmelzen zweier Routen (4 Verbindungen)
        merged = False
        R = len(st.routes)
        for i in range(R):
            if merged:
                break
            for j in range(i + 1, R):
                if st.load[i] + st.load[j] > qmax:
                    continue
                ri_, rj_ = st.routes[i], st.routes[j]
                best = None
                for a in (ri_, ri_[::-1]):
                    for b in (rj_, rj_[::-1]):
                        cand = a + b
                        ln = M.route_len(D, cand)
                        if best is None or ln < best[0]:
                            best = (ln, cand)
                delta = rc(best[0], st.load[i] + st.load[j]) - rc(st.len[i], st.load[i]) - rc(st.len[j], st.load[j])
                if delta < -EPS:
                    st.routes[i] = best[1]
                    st.routes[j] = []
                    st.refresh(i)
                    st.compact()
                    improved = merged = True
                    break
    st.compact()
    return st


def _recreate(st, removed, rng, noise):
    inst, D, rc = st.inst, st.inst.D, st.rc
    for c in removed:
        d = inst.dem[c]
        best = None
        for ri, r in enumerate(st.routes):
            if st.load[ri] + d > st.qmax:
                continue
            base = rc(st.len[ri], st.load[ri])
            for q in range(len(r) + 1):
                delta = rc(st.len[ri] + _ins_cost(D, r, q, c), st.load[ri] + d) - base
                key = delta * (1.0 + noise * (rng.uniform() - 0.5))
                if best is None or key < best[0]:
                    best = (key, ri, q)
        new_key = rc(2 * D[0][c], d) * (1.0 + noise * (rng.uniform() - 0.5))
        if best is None or new_key < best[0]:
            ri = st.add_route()
            st.routes[ri].append(c)
            st.refresh(ri)
        else:
            _, ri, q = best
            st.routes[ri].insert(q, c)
            st.refresh(ri)


# ------------------------------------------------------------------------------------------------ Packungsstart (deterministisch)

def pack_bins(dem, V, Q, node_limit=PACK_NODES):
    """Verteilt die Mengen `dem` (Liste, Index 0 = Depot = 0) auf V Behälter der Größe Q, nur Zulässigkeit.

    Behälter für Behälter: Der erste Behälter enthält die größte noch offene Menge (jede Packung lässt sich so ordnen), danach wählt die
    Tiefensuche je Mengenstufe, wie viele Kunden dieser Menge in den Behälter kommen (größere Anzahl zuerst). Ein Behälter darf höchstens den
    noch freien Gesamtplatz V · Q − Σd (Reserve) verschwenden; Zustände (Restmenge je Stufe), die schon scheiterten, werden nicht wiederholt.
    Nur Ganzzahlen, keine Zeit: nach `node_limit` Knoten gibt sie None zurück. Liefert eine Liste von V Kundenlisten oder None."""
    custs = list(range(1, len(dem)))
    total = sum(dem[c] for c in custs)
    if V * Q < total or any(dem[c] > Q for c in custs):
        return None
    sizes = sorted({dem[c] for c in custs}, reverse=True)
    by_size = {s: sorted(c for c in custs if dem[c] == s) for s in sizes}
    cnt = [len(by_size[s]) for s in sizes]
    m = len(sizes)
    nodes = [0]
    failed = set()
    plan = []                                  # je Behälter die Zahl der Kunden je Mengenstufe

    def fill(b, slack):
        if b == V - 1:                         # letzter Behälter: der Rest passt, weil slack >= 0 gilt
            plan.append(cnt[:])
            return True
        state = tuple(cnt)
        if state in failed:
            return False
        first = next((i for i in range(m) if cnt[i] > 0), None)
        if first is None:                      # alles verteilt, übrige Behälter bleiben leer
            return False
        take = [0] * m

        def pick(i, load):
            nodes[0] += 1
            if nodes[0] > node_limit:
                return False
            rem = sum(cnt[j] * sizes[j] for j in range(i, m))
            if load + rem < Q - slack:         # selbst mit allem Übrigen zu leer: mehr als die Reserve verschwendet
                return False
            if i == m:
                waste = Q - load
                if waste > slack:
                    return False
                plan.append(take[:])
                for j in range(m):
                    cnt[j] -= take[j]
                if fill(b + 1, slack - waste):
                    return True
                for j in range(m):
                    cnt[j] += take[j]
                plan.pop()
                return False
            s = sizes[i]
            hi = min(cnt[i], (Q - load) // s)
            lo = 1 if i == first else 0
            for c in range(hi, lo - 1, -1):
                take[i] = c
                if pick(i + 1, load + c * s):
                    return True
                if nodes[0] > node_limit:
                    take[i] = 0
                    return False
            take[i] = 0
            return False

        ok = pick(0, 0)
        if not ok and nodes[0] <= node_limit:
            failed.add(state)
        return ok

    if not fill(0, V * Q - total):
        return None
    left = {s: iter(by_size[s]) for s in sizes}
    bins = []
    for row in plan:
        bl = []
        for i, s in enumerate(sizes):
            for _ in range(row[i]):
                bl.append(next(left[s]))
        bins.append(sorted(bl))
    return bins


_PACK_CACHE = {}


def pack_start(inst):
    """Packungsstart: gibt es eine Zuordnung der Kunden auf ⌈Σd / Q⌉ Fahrzeuge? Wenn ja Routen aus den Behältern (Reihenfolge Nächster
    Nachbar vom Depot, Gleichstand kleinerer Kunde), sonst None. Hilft bei knapper Kapazität, wo die Suche allein die perfekte Packung selten findet."""
    key = (tuple(inst.dem), inst.Q)
    if key in _PACK_CACHE:
        return _PACK_CACHE[key]
    V = M.lower_bound_vehicles(inst)
    bins = pack_bins(inst.dem, V, inst.Q)
    res = None
    if bins is not None:
        res = []
        D = inst.D
        for bl in bins:
            r, left, cur = [], set(bl), 0
            while left:
                nxt = min(left, key=lambda c: (D[cur][c], c))
                r.append(nxt)
                left.remove(nxt)
                cur = nxt
            res.append(r)
    _PACK_CACHE[key] = res
    return res


# ------------------------------------------------------------------------------------------------ ILS und Löser

def _ils(inst, f_int, iters, seed, start, start_cost):
    """ILS (Ruin-and-Recreate, Annahme nach Record-to-Record 0,4 %) ab einer Startlösung; das Beste wird mitgeführt."""
    rc = _make_rc(f_int)
    rng = SplitMix64(seed * 1000003 + 17)
    st = _local_search(St(inst, start, rc))
    best = [r[:] for r in st.routes]
    best_c = st.cost()
    if start_cost < best_c:
        best, best_c = [r[:] for r in start], start_cost
    cur = [r[:] for r in best]
    stale = 0
    n = inst.n
    for _ in range(iters):
        s2 = St(inst, cur, rc)
        kmax = max(4, n // 3)
        k = min(n, 2 + rng.below(kmax - 1))
        u = rng.uniform()
        if u < 0.34:
            pool = list(range(1, n + 1))
            removed = []
            for _j in range(k):
                removed.append(pool.pop(rng.below(len(pool))))
        elif u < 0.67:
            seed_c = 1 + rng.below(n)
            removed = [seed_c] + inst.neighbors(10)[seed_c][:k - 1]
        else:
            ri0 = rng.below(len(s2.routes))
            removed = s2.routes[ri0][:]
            if rng.uniform() < 0.5 and len(s2.routes) > 1:
                c0 = removed[rng.below(len(removed))]
                for v in inst.neighbors(10)[c0]:
                    if s2.where[v][0] != ri0:
                        removed += s2.routes[s2.where[v][0]]
                        break
        for c in removed:
            ri, _ = s2.where[c]
            s2.routes[ri].remove(c)
            s2.refresh(ri)
        s2.compact()
        order = removed[:]
        for i in range(len(order) - 1, 0, -1):
            j = rng.below(i + 1)
            order[i], order[j] = order[j], order[i]
        _recreate(s2, order, rng, 0.3)
        s2.compact()
        _local_search(s2)
        c2 = s2.cost()
        if c2 < best_c - EPS:
            best_c = c2
            best = [r[:] for r in s2.routes]
            stale = 0
        else:
            stale += 1
        if c2 <= best_c * 1.004:
            cur = [r[:] for r in s2.routes]
        if stale >= 80:
            cur = [r[:] for r in best]
            stale = 0
    return best


def solve_fix(inst, f_int, iters, seed, starts=None):
    """Beste Suche aus der günstigsten Startlösung (Warmstarts `starts`, Clarke-Wright) und, bei knapper Kapazität (Clarke-Wright braucht mehr
    Fahrzeuge als die untere Schranke ⌈Σd / Q⌉), zusätzlich aus dem Packungsstart. Das Ergebnis ist nie teurer als die beste Startlösung."""
    cand = []
    for s in (starts or []):
        cand.append(([r[:] for r in s if r], M.total_cost(inst, s, f_int)))
    sav = M.savings_pure(inst)
    cand.append((sav, M.total_cost(inst, sav, f_int)))
    pk = None
    if len(sav) > M.lower_bound_vehicles(inst):
        pk = pack_start(inst)
    cand.sort(key=lambda t: t[1])
    best = _ils(inst, f_int, iters, seed, cand[0][0], cand[0][1])
    best_c = M.total_cost(inst, best, f_int)
    if pk is not None:
        pk_c = M.total_cost(inst, pk, f_int)
        alt = _ils(inst, f_int, iters, seed, pk, pk_c)
        alt_c = M.total_cost(inst, alt, f_int)
        if alt_c < best_c - EPS:
            best, best_c = alt, alt_c
    return best


FS = (0, 10, 25, 50, 100, 200, 400)      # Fixkostenstufen der Messreihe (Längeneinheiten je Fahrzeug)


def chain(inst, fs, iters, seed):
    """Messreihen-Kette: Lösungen für alle f in `fs` in zwei Durchgängen (aufsteigend, dann absteigend, Warmstarts aus allen bisherigen
    Lösungen); für jedes f die billigste aller gefundenen Lösungen. Rückgabe {f: Routen}."""
    starts = []
    sols = {}
    for f in fs:
        sols[f] = solve_fix(inst, f * M.SCALE, iters, seed, starts)
        starts.append(sols[f])
    for f in reversed(fs):
        alt = solve_fix(inst, f * M.SCALE, iters, seed + 7, starts)
        starts.append(alt)
        if M.total_cost(inst, alt, f * M.SCALE) < M.total_cost(inst, sols[f], f * M.SCALE):
            sols[f] = alt
    for f in fs:
        sols[f] = min(starts + [sols[f]], key=lambda r: M.total_cost(inst, r, f * M.SCALE))
    return sols


def short_chain(inst, fs, iters, seed):
    """Live-Kette der App: ein Durchgang aufsteigend in f mit Warmstarts aus den kleineren f (fs aufsteigend sortiert); für jedes f die billigste
    aller gefundenen Lösungen. Rückgabe {f: Routen}."""
    fs = sorted(set(fs))
    starts = []
    sols = {}
    for f in fs:
        sols[f] = solve_fix(inst, f * M.SCALE, iters, seed, starts)
        starts.append(sols[f])
    for f in fs:
        sols[f] = min(starts, key=lambda r: M.total_cost(inst, r, f * M.SCALE))
    return sols
