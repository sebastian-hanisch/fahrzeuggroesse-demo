"""Instanz, Kapazität, Kosten und Prüfer von Hand."""

import pytest

import fgr_model as M


def test_gerade_entfernungen_und_tourlaenge_von_hand(gerade):
    assert gerade.D[0][1] == 100 and gerade.D[0][3] == 300 and gerade.D[1][3] == 200       # 10, 30 und 20 Längeneinheiten, je mal 10
    assert M.route_len(gerade.D, [2, 3]) == 200 + 100 + 300                                  # 0 -> 2 -> 3 -> 0: 20 + 10 + 30 Längeneinheiten
    assert M.route_len(gerade.D, []) == 0


def test_gesamtkosten_sind_fixkosten_mal_fahrzeuge_plus_distanz(gerade):
    routes = [[1], [2, 3]]
    assert M.distance_of(gerade, routes) == 200 + 600
    assert M.total_cost(gerade, routes, 0) == 800
    assert M.total_cost(gerade, routes, 1000) == 800 + 2 * 1000                              # f = 100 Längeneinheiten = 1000 Einheiten
    assert M.total_cost(gerade, [[1], [], [2, 3]], 1000) == 2800                              # leere Tour kostet nichts


def test_pruefer_erkennt_ueberlast_doppelte_und_fehlende_kunden(gerade):
    assert M.verify(gerade, [[1], [2, 3]]) == []
    assert M.verify(gerade, [[1, 2, 3]])                       # Überlast 30 > 20
    assert M.verify(gerade, [[1], [1, 2, 3]])                  # Kunde 1 doppelt (und Überlast)
    assert M.verify(gerade, [[1], [2]])                        # Kunde 3 fehlt
    assert M.verify(gerade, [[1], [], [2, 3]])                 # leere Tour


def test_kapazitaet_aus_ladungen_und_reserve_von_hand():
    dem = [0, 10, 10, 10]                                      # Summe 30
    assert M.capacity(dem, 2, 0.0) == 15 and M.capacity(dem, 3, 0.0) == 10
    assert M.capacity(dem, 2, 0.10) == 17                      # ⌈1,1 · 30 / 2⌉ = ⌈16,5⌉
    assert M.capacity([0, 5, 25], 5, 0.0) == 25                # mindestens die größte Einzelmenge (⌈30 / 5⌉ = 6)


def test_untere_schranke_der_fahrzeugzahl(gerade):
    assert M.lower_bound_vehicles(gerade) == 2                 # ⌈30 / 20⌉


def test_erste_instanz_der_messreihe_hat_die_bekannten_kennzahlen():
    inst = M.make_instance(20, "rand", 300000, 3, 0.0)
    assert (inst.Q, sum(inst.dem), M.lower_bound_vehicles(inst)) == (111, 332, 3)
    assert round(M.depot_dist_mean(inst), 1) == 573.2
    assert all(5 <= d <= 25 for d in inst.dem[1:]) and inst.dem[0] == 0 and len(inst.xy) == 21


def test_instanz_ist_deterministisch_und_beide_depots_haben_dieselben_kunden():
    a, b = M.make_instance(20, "rand", 7, 5, 0.02), M.make_instance(20, "rand", 7, 5, 0.02)
    c = M.make_instance(20, "mitte", 7, 5, 0.02)
    assert a.xy == b.xy and a.dem == b.dem and a.D == b.D
    assert a.xy[1:] == c.xy[1:] and a.dem == c.dem and a.xy[0] != c.xy[0]


def test_entfernungsmatrix_ist_symmetrisch_ganzzahlig_und_erfuellt_die_dreiecksungleichung_bis_auf_rundung():
    inst = M.make_instance(20, "mitte", 11, 3, 0.0)
    for i in range(21):
        assert inst.D[i][i] == 0
        for j in range(21):
            assert inst.D[i][j] == inst.D[j][i] and isinstance(inst.D[i][j], int)
            for k in range(21):
                assert inst.D[i][j] <= inst.D[i][k] + inst.D[k][j] + 1          # Rundung: höchstens eine Einheit


def test_savings_ist_zulaessig_und_deterministisch():
    inst = M.make_instance(20, "rand", 300003, 5, 0.0)
    r1, r2 = M.savings_pure(inst), M.savings_pure(inst)
    assert r1 == r2 and M.verify(inst, r1) == []


@pytest.mark.parametrize("n", [1, 2])
def test_kleinste_instanzen(n):
    inst = M.make_instance(n, "rand", 5, 1, 0.0)
    assert inst.Q >= max(inst.dem[1:]) and M.lower_bound_vehicles(inst) >= 1
    assert M.verify(inst, M.savings_pure(inst)) == []
