"""Laden und Auswerten der vorgerechneten Messreihe (data/fgr_results.json, erzeugt von tools/dump_results.py aus tools/messreihe.py).

Alle Zahlen der App stammen aus dieser Datei (`tests/test_claims.py` rechnet sie nach). Inhalt:
  cells        40 Zellen des Hauptrasters (n 20/40 · Depot · 10 Kapazitäten · je 25 Instanzen, 7 Fixkostenstufen); 32 davon mit k in {3, 5} sind die Ampel-Zellen
  by_reserve   Zählungen über die Instanzen je Reserve (k in {3, 5}, je 200 Instanzen)
  factors      Anteil der Front-Zellen je Stufe der Faktoren Reserve, k, n, Depot
  formel       Anpassung von a und b (192 Lösungen) und Fehler in 16 Zellen; qstern: Größenwahl über Kostenfamilien
  ort, orakel, mengen   OR-Tools-Vergleich, Orakel bei n = 12, andere Mengenverteilungen
  vormessung   nicht neu gerechnete Zahlen der Vormessung (Packungsstart damals CP-SAT)
"""

import json
import pathlib
from functools import lru_cache

import fgr_constants as C

DATA = pathlib.Path(__file__).resolve().parent / "data"
ORDER = ("n", "depot", "k", "s")
AXES = {"n": C.N_OPTIONS, "depot": C.DEPOT_OPTIONS, "k": C.K_OPTIONS, "s": C.RESERVE_OPTIONS}
KLASS_LABEL = {"front": "Zielkonflikt", "zwischen": "Grenzfall", "keine": "kein Zielkonflikt"}


@lru_cache(maxsize=1)
def load():
    return json.loads((DATA / "fgr_results.json").read_text(encoding="utf-8"))


def cells(ampel_only=True):
    cs = load()["cells"]
    return [c for c in cs if c["ampel"]] if ampel_only else cs


def cell_of(n, depot, k, reserve):
    """Die gemessene Zelle zu einer Einstellung der App (alle Regler stehen auf gemessenen Stufen)."""
    for c in load()["cells"]:
        if (c["n"], c["depot"], c["k"]) == (n, depot, k) and abs(c["s"] - reserve) < 1e-9:
            return c
    raise KeyError((n, depot, k, reserve))


def klass_counts():
    cs = cells()
    return {key: sum(1 for c in cs if c["klass"] == key) for key in ("front", "zwischen", "keine")}


def reserve_counts(reserve):
    """Zahl der Front-, Grenzfall- und Keine-Front-Zellen bei einer Reserve (Ampel-Zellen: 8 je Reserve)."""
    cs = [c for c in cells() if abs(c["s"] - reserve) < 1e-9]
    return {"zellen": len(cs), **{key: sum(1 for c in cs if c["klass"] == key) for key in ("front", "zwischen", "keine")}}


def by_reserve(reserve):
    return load()["by_reserve"][str(reserve)]


SEPARATE_HI, SEPARATE_LO = 0.6, 0.2          # Maßstab: ein Faktor „trennt“, wenn der Anteil Zielkonflikt-Zellen auf einer Stufe mindestens 60 % und auf einer anderen höchstens 20 % beträgt
FACTOR_LABEL = {"s": "Reserve", "k": "Ladungen", "n": "Kundenzahl", "depot": "Depot"}


def separating_factors():
    """Faktoren (s, k, n, depot), deren Stufen die Zielkonflikt-Zellen trennen: höchster Anteil >= 60 % und niedrigster <= 20 %."""
    out = []
    for fac, levels in load()["factors"].items():
        shares = [v["share"] for v in levels.values()]
        if max(shares) >= SEPARATE_HI and min(shares) <= SEPARATE_LO:
            out.append(fac)
    return out


def percent_key(value):
    return str(float(value))


def num(x, digits=1, sign=False):
    return (f"{x:+.{digits}f}" if sign else f"{x:.{digits}f}").replace(".", ",")


def fpair_text(d):
    """Median und Quartile des rechnerischen Kipppunkts f* = (D₄₀₀ − D₀) / (V₀ − V₄₀₀) der Instanzen mit weniger Fahrzeugen (Quartile durch Interpolation zwischen den Instanzwerten)."""
    return f"Median {num(d['fpair_median'], 1)} (Quartile {', '.join(num(q, 1) for q in d['fpair_quartiles'])}; Interpolation zwischen Instanzwerten)"


def numshort(x):
    """Zahl mit Dezimalkomma, ganze Zahlen ohne Nachkommastelle (50 statt 50,0), sonst eine Stelle (62,5; nie auf 62 gerundet)."""
    return num(x, 0) if abs(x - round(x)) < 1e-9 else num(x, 1)


def pct(x, digits=0):
    """Anteil (0 bis 1) als Prozentzahl mit Komma, ohne Prozentzeichen."""
    return num(100.0 * x, digits)


def minus(text):
    """Echtes Minuszeichen statt Bindestrich."""
    return text.replace("-", "−")


def fstar_counts_text(counts):
    return " / ".join(str(counts[str(f)]) for f in C.FIX_OPTIONS[1:])
