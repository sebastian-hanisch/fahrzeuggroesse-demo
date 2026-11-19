"""Randfälle (DEMO-PLAYBOOK §12): ein Kunde, zwei Kunden, Kapazität gleich der größten Menge, gleiche Mengen, Fixkosten 0 und am Rand."""

import pytest

import fgr_evaluation as E
import fgr_model as M
import fgr_search as S
import fgr_solvers as V


def test_ein_kunde_eine_tour():
    inst = M.make_custom([(0.0, 0.0), (10.0, 0.0)], [0, 7], 7)
    routes = S.solve_fix(inst, 500, 10, 1)
    assert routes == [[1]] and M.total_cost(inst, routes, 500) == 200 + 500
    assert V.exact_optima(inst, [500]) == {500: 700}


def test_zwei_kunden_eine_oder_zwei_touren_je_nach_kapazitaet():
    xy = [(0.0, 0.0), (10.0, 0.0), (-10.0, 0.0)]
    eng = M.make_custom(xy, [0, 5, 5], 5)          # jeder Kunde füllt ein Fahrzeug
    weit = M.make_custom(xy, [0, 5, 5], 10)
    assert len(S.solve_fix(eng, 0, 10, 1)) == 2
    assert len(S.solve_fix(weit, 1000, 10, 1)) == 1   # mit Fixkosten: eine Tour (Länge 400) statt zwei (auch 400): das zweite Fahrzeug kostet nur Fixkosten; ohne Fixkosten sind beide gleich teuer
    assert V.exact_optima(weit, [0, 1000]) == {0: 400, 1000: 1400}


def test_kapazitaet_gleich_der_groessten_menge_gleiche_mengen_gleichstand():
    inst = M.make_custom([(0.0, 0.0), (10.0, 0.0), (20.0, 0.0), (30.0, 0.0)], [0, 10, 10, 10], 10)
    routes = S.solve_fix(inst, 0, 20, 1)
    assert M.verify(inst, routes) == [] and len(routes) == 3
    assert V.exact_optima(inst, [0]) == {0: 2 * (100 + 200 + 300)}


@pytest.mark.parametrize("f", [0, 400])
def test_fixkosten_am_rand_der_stufen(f):
    inst = M.make_instance(20, "rand", 300000, 5, 0.0)
    routes = S.solve_fix(inst, f * M.SCALE, 20, 3)
    assert M.verify(inst, routes) == []


def test_tipping_point_ohne_weniger_fahrzeuge_und_mit_dominierender_loesung():
    def sol(key, v, d):
        return E.Sol(key, key, 0, (), d, v)
    assert E.tipping_point(sol("a", 5, 1000), sol("b", 5, 1200)) is None          # gleiche Fahrzeugzahl: kein Kipppunkt
    assert E.tipping_point(sol("a", 6, 1000), sol("b", 5, 900)) == 0.0            # weniger Fahrzeuge und kürzer: schon bei f = 0 besser
    assert E.tipping_point(sol("a", 6, 1000), sol("b", 5, 1500)) == pytest.approx(50.0)   # (1500 − 1000) / 10 Einheiten = 50 Längeneinheiten, ein Fahrzeug weniger
    assert E.tipping_point(sol("a", 6, 1000), sol("b", 4, 1500)) == pytest.approx(25.0)   # zwei Fahrzeuge weniger: die Hälfte
