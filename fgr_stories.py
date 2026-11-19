"""Abnahmekriterien der Presets: was der angezeigte Lauf jedes Presets qualitativ zeigen muss.

Die Aussage der Demo stützt sich auf die Messreihe (25 Instanzen je Zelle); ein Preset zeigt nur einen Lauf, der zur Geschichte passt. Die Kriterien sind deshalb bewusst grob und
prüfen den Lauf, nicht die Messreihe. Zufalls-Seeds der Presets ab 500000 (nie 1000 bis 1011, 2000 bis 2007, 300000 bis 300024 und 310000 bis 310007 der Messreihen); die Suche steht in
tools/find_preset_seeds.py."""

import fgr_evaluation as E


def _tp(a):
    return E.tipping_point(E.sol_of(a, "f0"), E.sol_of(a, "f400"))


def story_standard(a, settings):
    """Zielkonflikt auf dieser Instanz, und das gewählte f liegt über dem Kipppunkt: die kostenoptimale Lösung hat so viele Fahrzeuge wie die bei f = 400 und weniger als die kürzeste."""
    f0, sel, f400 = (E.sol_of(a, key) for key in ("f0", "sel", "f400"))
    tp = _tp(a)
    return tp is not None and 0 < tp <= settings.fix and sel.vehicles == f400.vehicles < f0.vehicles


def story_knapp_klein(a, settings):
    """Die Lösung bei f = 400 hat weniger Fahrzeuge als die kürzeste und ist mindestens 5 % länger."""
    f0, f400 = E.sol_of(a, "f0"), E.sol_of(a, "f400")
    return f400.vehicles < f0.vehicles and f400.dist >= 1.05 * f0.dist


def story_grenzfall(a, settings):
    """Eine der Instanzen mit Zielkonflikt: weniger Fahrzeuge bei f = 400 und ein kleiner, aber erkennbarer Kipppunkt (über 2 und höchstens 10, nicht der Rauschbereich nahe null)."""
    f0, f400 = E.sol_of(a, "f0"), E.sol_of(a, "f400")
    tp = _tp(a)
    return f400.vehicles < f0.vehicles and tp is not None and 2 < tp <= 10


def story_genug_reserve(a, settings):
    """Kein Zielkonflikt: die Fahrzeugzahl ist bei f = 0 und bei f = 400 gleich."""
    return E.sol_of(a, "f0").vehicles == E.sol_of(a, "f400").vehicles


def story_wenige_ladungen(a, settings):
    """Zielkonflikt mit niedrigem, aber erkennbarem Kipppunkt: weniger Fahrzeuge bei f = 400 und f* über 5 und höchstens 25."""
    f0, f400 = E.sol_of(a, "f0"), E.sol_of(a, "f400")
    tp = _tp(a)
    return f400.vehicles < f0.vehicles and tp is not None and 5 < tp <= 25


STORIES = {
    "Standard": story_standard,
    "Knappe Kapazität, 20 Kunden": story_knapp_klein,
    "Grenzfall: 2 % Reserve": story_grenzfall,
    "Genug Reserve": story_genug_reserve,
    "Wenige Ladungen": story_wenige_ladungen,
}
