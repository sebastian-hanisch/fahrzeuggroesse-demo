"""Eigene Suche: Invarianten, Packungsstart, Kette und Reproduzierbarkeit (die Güte gegen ein Optimum steht in test_oracle_fahrzeuggroesse.py)."""

import pytest

import fgr_model as M
import fgr_search as S

ITERS = 40


def _inst(n=20, depot="rand", seed=300000, k=3, s=0.0):
    return M.make_instance(n, depot, seed, k, s)


@pytest.mark.parametrize("f", [0, 100, 400])
def test_suche_liefert_zulaessige_loesung_ohne_leere_touren(f):
    inst = _inst(seed=300001, k=5)
    routes = S.solve_fix(inst, f * M.SCALE, ITERS, 7)
    assert M.verify(inst, routes) == []
    assert len(routes) >= M.lower_bound_vehicles(inst)


def test_suche_ist_nie_schlechter_als_savings_und_gleicher_zufalls_seed_gleiche_loesung():
    inst = _inst(seed=300002, k=5, s=0.02)
    f_int = 50 * M.SCALE
    r1, r2 = S.solve_fix(inst, f_int, ITERS, 3), S.solve_fix(inst, f_int, ITERS, 3)
    assert r1 == r2
    assert M.total_cost(inst, r1, f_int) <= M.total_cost(inst, M.savings_pure(inst), f_int)


def test_hohe_fixkosten_senken_die_fahrzeugzahl_auf_der_gerade(gerade):
    # Von Hand: Optimum {1}, {2, 3} (Länge 80, zwei Fahrzeuge); eine Tour mit allen drei ist wegen Q = 20 unzulässig
    for f in (0, 100):
        routes = S.solve_fix(gerade, f * M.SCALE, 30, 3)
        assert M.total_cost(gerade, routes, f * M.SCALE) == 800 + 2 * f * M.SCALE
        assert sorted(sorted(r) for r in routes) == [[1], [2, 3]]


def test_kette_gibt_je_f_die_billigste_der_gefundenen_loesungen():
    inst = _inst(n=20, depot="mitte", seed=300003, k=5)
    fs = (0, 100, 400)
    sols = S.short_chain(inst, fs, ITERS, 5)
    assert set(sols) == set(fs)
    for f in fs:
        assert M.verify(inst, sols[f]) == []
        # die Lösung zu f ist bei f nie teurer als die zu einem anderen f gefundene
        assert M.total_cost(inst, sols[f], f * M.SCALE) <= min(M.total_cost(inst, sols[g], f * M.SCALE) for g in fs)


def test_fahrzeugzahl_sinkt_im_mittel_nicht_steigend_ueber_f_und_zweig_bei_knapper_kapazitaet():
    """Zweig-Test (Nullspalten-Falle): bei Reserve 0 % sinkt V auf mindestens einer Instanz von f = 0 auf f = 400; im Mittel steigt V nie mit f."""
    drops, sums = 0, {0: 0, 400: 0}
    for seed in range(300000, 300005):
        inst = _inst(n=20, depot="mitte", seed=seed, k=5, s=0.0)
        sols = S.short_chain(inst, (0, 400), ITERS, seed)
        v0, v1 = len(sols[0]), len(sols[400])
        sums[0] += v0
        sums[400] += v1
        drops += v1 < v0
    assert drops >= 1
    assert sums[400] <= sums[0]


# ------------------------------------------------------------------------------------------------ Packungsstart

def _check_packing(dem, bins, V, Q):
    assert len(bins) == V
    assert sorted(c for bl in bins for c in bl) == list(range(1, len(dem)))
    assert all(sum(dem[c] for c in bl) <= Q for bl in bins)


def test_packung_von_hand():
    dem = [0, 6, 4, 5, 5]                                      # 6 + 4 und 5 + 5 füllen zwei Behälter der Größe 10 exakt
    bins = S.pack_bins(dem, 2, 10)
    _check_packing(dem, bins, 2, 10)
    assert sorted(sorted(bl) for bl in bins) == [[1, 2], [3, 4]]


def test_packung_unmoeglich_gibt_none():
    assert S.pack_bins([0, 6, 6, 6], 2, 10) is None            # drei Sechser brauchen drei Behälter
    assert S.pack_bins([0, 11], 1, 10) is None                 # Menge größer als die Kapazität
    assert S.pack_bins([0, 5, 5, 5], 1, 10) is None            # Summe größer als V · Q


def test_packung_ist_deterministisch_und_erreicht_die_untere_schranke_bei_knapper_kapazitaet():
    found = 0
    for seed in range(300000, 300012):
        inst = _inst(n=40, depot="rand", seed=seed, k=5, s=0.0)
        V = M.lower_bound_vehicles(inst)
        b1, b2 = S.pack_bins(inst.dem, V, inst.Q), S.pack_bins(inst.dem, V, inst.Q)
        assert b1 == b2
        if b1 is not None:
            _check_packing(inst.dem, b1, V, inst.Q)
            found += 1
    assert found >= 10          # bei 12 Instanzen gefunden: gemessen 12 (Reserve 0 %, 5 Ladungen, 40 Kunden); Band statt exakter Zahl


def test_packung_mit_knotengrenze_bricht_ab_statt_zu_haengen():
    inst = _inst(n=40, depot="rand", seed=300004, k=5, s=0.0)
    assert S.pack_bins(inst.dem, M.lower_bound_vehicles(inst), inst.Q, node_limit=1) is None


def test_packungsstart_liefert_touren_aus_den_behaeltern():
    inst = _inst(n=20, depot="rand", seed=300000, k=3, s=0.0)
    routes = S.pack_start(inst)
    assert routes is not None and M.verify(inst, routes) == [] and len(routes) == M.lower_bound_vehicles(inst)
