"""Neu-Rechnen als Band (DEMO-PLAYBOOK §5, „letztes Bit“): drei Instanzen der Messreihe werden mit der Kette der Demo (100 Iterationen, drei Stufen) neu gerechnet und mit den beim Bau
erhaltenen Werten verglichen. Die Suche ist deterministisch und rechnet mit Ganzzahlen; die Entfernungen kommen aus `math.hypot` und Rundung, die Zufallszahlen aus SplitMix64 (nur Ganzzahlen).
Auf einer anderen Plattform darf die letzte Binärstelle einer Entfernung anders ausfallen, darum gilt für Kosten ein Band von 3 % und für die Fahrzeugzahl ±1, nicht Gleichheit."""

import pytest

import fgr_model as M
import fgr_search as S

# (n, Depot, Zufalls-Seed, k, Reserve): Kapazität Q, dann je f in (0, 100, 400): (Fahrzeuge, Distanz)
FAELLE = [
    ((20, "mitte", 300000, 5, 0.0), 67, {0: (6, 6230), 100: (6, 6230), 400: (5, 7422)}),
    ((20, "rand", 300002, 3, 0.02), 106, {0: (3, 5641), 100: (3, 5641), 400: (3, 5641)}),
    ((20, "rand", 300005, 5, 0.1), 70, {0: (5, 7189), 100: (5, 7189), 400: (5, 7189)}),
]


@pytest.mark.parametrize("args,Q,erwartet", FAELLE)
def test_neu_rechnen_liegt_im_band(args, Q, erwartet):
    n, depot, seed, k, s = args
    inst = M.make_instance(n, depot, seed, k, s)
    assert inst.Q == Q                                                       # Kapazität aus Ganzzahlen: exakt
    sols = S.chain(inst, (0, 100, 400), 100, seed)
    for f, (v, d) in erwartet.items():
        assert M.verify(inst, sols[f]) == []
        assert abs(len(sols[f]) - v) <= 1, (f, len(sols[f]), v)
        cost, ref = M.total_cost(inst, sols[f], f * M.SCALE), v * f * M.SCALE + d
        assert cost == pytest.approx(ref, rel=0.03), (f, cost, ref)

