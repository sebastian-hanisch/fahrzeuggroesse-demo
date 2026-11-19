"""Gemeinsame Fixtures: die Mini-Instanz, an der jede Einheit von Hand geprüft wird (DEMO-PLAYBOOK §1b)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fgr_model as M  # noqa: E402


@pytest.fixture
def gerade():
    """Gerade, Depot links: Kunden bei 10, 20, 30 Längeneinheiten mit Menge 10 je, Kapazität 20.
    Von Hand: Optimum {1}, {2, 3}: Länge 2 · 10 + 2 · 30 = 80 Längeneinheiten (800 Einheiten); mit Fixkosten f je Fahrzeug 80 + 2 f."""
    return M.make_custom([(0.0, 0.0), (10.0, 0.0), (20.0, 0.0), (30.0, 0.0)], [0, 10, 10, 10], 20)


@pytest.fixture
def schnelle_suche(monkeypatch):
    """App-Tests rechnen die Live-Suche mit höchstens 15 Iterationen (die Zahlen der App sind dann nicht die der Messreihe; geprüft wird Ablauf, nicht Güte)."""
    import fgr_search as S
    orig_short, orig_fix = S.short_chain, S.solve_fix
    monkeypatch.setattr(S, "short_chain", lambda inst, fs, iters, seed: orig_short(inst, fs, min(iters, 15), seed))
    monkeypatch.setattr(S, "solve_fix", lambda inst, f_int, iters, seed, starts=None: orig_fix(inst, f_int, min(iters, 15), seed, starts))
