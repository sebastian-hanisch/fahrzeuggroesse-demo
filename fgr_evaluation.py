"""Live-Analyse einer Instanz (kürzeste, gewählte und die Lösung bei f = 400), Kennzahlen und Verdikte als reine Funktionen: verdict_*(...) -> (Art, Text)."""

import time
from dataclasses import dataclass

import fgr_constants as C
import fgr_model as M
import fgr_results as R
import fgr_search as SR


@dataclass(frozen=True)
class Settings:
    n: int = C.DEFAULT_N
    depot: str = C.DEFAULT_DEPOT
    k: int = C.DEFAULT_K
    reserve: float = C.DEFAULT_RESERVE
    fix: int = C.DEFAULT_FIX
    ils: int = C.DEFAULT_ILS
    seed: int = C.DEFAULT_SEED


@dataclass(frozen=True)
class Sol:
    key: str              # "f0" (kürzeste), "sel" (kostenoptimal bei dem gewählten f), "f400" (Lösung bei f = 400)
    label: str
    f: int                # Fixkosten, bei denen die Lösung gesucht wurde
    routes: tuple         # Tuple von Tuples (hashbar für den Cache)
    dist: int             # Entfernungseinheiten (0,1 Längeneinheit)
    vehicles: int


@dataclass(frozen=True)
class Analysis:
    inst: M.Instance
    sols: tuple
    seconds: float


def make_inst(settings: Settings) -> M.Instance:
    return M.make_instance(settings.n, settings.depot, settings.seed, settings.k, settings.reserve)


def _freeze(routes):
    return tuple(tuple(r) for r in routes)


def analyse(settings: Settings) -> Analysis:
    """Live-Kette: eine Suche je Fixkostenstufe 0, gewählt, 400 (ein Durchgang aufsteigend mit Warmstarts); die Messreihe rechnet sieben Stufen in zwei
    Durchgängen. Deterministisch bei gleichem Zufalls-Seed und gleicher Iterationszahl."""
    inst = make_inst(settings)
    t0 = time.perf_counter()
    sols = SR.short_chain(inst, (0, settings.fix, C.FIX_MAX), settings.ils, settings.seed)
    secs = time.perf_counter() - t0
    out = []
    for key, f, label in (("f0", 0, "Kürzeste Lösung (f = 0)"), ("sel", settings.fix, f"Kostenoptimal bei f = {settings.fix}"),
                          ("f400", C.FIX_MAX, f"Lösung bei f = {C.FIX_MAX}")):
        r = sols[f]
        out.append(Sol(key, label, f, _freeze(r), M.distance_of(inst, r), len([x for x in r if x])))
    return Analysis(inst, tuple(out), secs)


def sol_of(a: Analysis, key: str) -> Sol:
    return next(s for s in a.sols if s.key == key)


def cost(sol: Sol, f: float) -> float:
    """Gesamtkosten f · V + D in Längeneinheiten bei den Fixkosten f (Längeneinheiten je Fahrzeug)."""
    return f * sol.vehicles + sol.dist / M.SCALE


def km(units: float) -> str:
    """Entfernung in Längeneinheiten des 100 × 100-Gebiets (1 Einheit der Rechnung = 0,1) mit Dezimalkomma."""
    return R.num(units / M.SCALE, 1)


def utilisation(inst: M.Instance, sol: Sol) -> float:
    """Auslastung der Fahrzeuge in Prozent: Σd / (V · Q)."""
    return 100.0 * sum(inst.dem[1:]) / (sol.vehicles * inst.Q)


def tipping_point(f0: Sol, f400: Sol):
    """Kipppunkt der beiden Lösungen in Längeneinheiten je Fahrzeug: ab diesem f ist die mit weniger Fahrzeugen die billigere (gleiche Gesamtkosten bei f* = ΔD / ΔV).
    None, wenn die Lösung bei f = 400 nicht weniger Fahrzeuge hat; 0, wenn sie bei weniger Fahrzeugen auch nicht länger ist."""
    dv = f0.vehicles - f400.vehicles
    if dv <= 0:
        return None
    dd = (f400.dist - f0.dist) / M.SCALE
    return max(0.0, dd / dv)


def minus_percent(saved: float) -> str:
    return f"−{R.num(saved)} %" if saved > 0 else "±0,0 %"


def reserve_text(reserve: float) -> str:
    return f"{R.num(100 * reserve, 0)} %"


def depot_text(depot: str) -> str:
    return "am Gebietsrand (50, 0)" if depot == "rand" else "in der Mitte des Gebiets (50, 50)"


def cell_text(cell) -> str:
    return (f"Zelle {cell['ci']}, {cell['n']} Kunden, Depot {depot_text(cell['depot'])}, {cell['k']} Ladungen, {reserve_text(cell['s'])} Reserve")


# ------------------------------------------------------------------------------------------------ Verdikte (reine Funktionen)

def klass_of(dv: float) -> str:
    """Klasse einer Zelle aus ΔV: 'front' (ab 0,3), 'keine' (unter 0,1), sonst 'zwischen'."""
    return "front" if dv >= C.FRONT_DV else ("keine" if dv < C.KEINE_DV else "zwischen")


def verdict_level(cell, fix: int):
    """Erste Meldung aus der vorgerechneten Zelle (nicht aus dem einen Lauf): kein Zielkonflikt, Grenzfall oder Zielkonflikt."""
    m = cell["m"]
    kl = klass_of(cell["dV"])
    n_f = cell["n_front_inst"]
    base = f"{cell_text(cell)}: ΔV = {R.num(cell['dV'], 2)} Fahrzeuge weniger bei f = 400 als bei f = 0 (Mittel über {m} Instanzen), in {n_f} von {m} Instanzen sinkt die Fahrzeugzahl."
    if fix > 0:
        less = cell["n_less_at_f"][str(fix)]
        at = f" Bei dem gewählten f = {fix} hat die kostenoptimale Lösung in {less} von {m} Instanzen weniger Fahrzeuge als die kürzeste."
    else:
        at = " Bei f = 0 gibt es nichts zu tauschen."
    if kl == "keine":
        return "success", (f"**Kein Zielkonflikt** (ΔV unter {R.num(C.KEINE_DV, 1)}). {base}{at} Die kürzeste Lösung nutzt im Mittel {R.num(cell['excess0'], 2)} Fahrzeuge mehr als die "
                           "untere Schranke ⌈Σd / Q⌉.")
    if kl == "front":
        return "warning", (f"**Zielkonflikt.** {base}{at} In diesen {n_f} Instanzen kostet die Lösung bei f = 400 im Mittel {R.num(cell['price_front_inst'])} % mehr Distanz als die kürzeste "
                           f"(rechnerischer Kipppunkt f* = (D₄₀₀ − D₀) / (V₀ − V₄₀₀) im Median {R.num(cell['fpair_median'], 1)}).")
    return "info", f"**Grenzfall (ΔV zwischen {R.num(C.KEINE_DV, 1)} und {R.num(C.FRONT_DV, 1)}).** {base}{at}"


def verdict_instance(settings: Settings, a: Analysis):
    """Meldung zur gezeigten Instanz: was hat die Suche gefunden (eine Instanz, kein Beleg)."""
    f0, f400 = sol_of(a, "f0"), sol_of(a, "f400")
    tp = tipping_point(f0, f400)
    if tp is None:
        return "info", (f"Auf dieser Instanz fand die Suche bei f = 400 keine Lösung mit weniger Fahrzeugen als bei f = 0 (beide {f0.vehicles}). "
                        "Das heißt nicht, dass es keine gibt (die Suche ist kein Beweis), nur: sie fand keine.")
    if tp <= 0:
        return "info", (f"Auf dieser Instanz ist die Lösung mit {f400.vehicles} statt {f0.vehicles} Fahrzeugen nicht länger ({km(f400.dist)} gegen {km(f0.dist)} Längeneinheiten): "
                        "kein Zielkonflikt, die Suche fand die kürzeste Lösung bei f = 0 nicht mit den wenigsten Fahrzeugen.")
    return "info", (f"Auf dieser Instanz fand die Suche {f0.vehicles} Fahrzeuge bei {km(f0.dist)} Längeneinheiten (f = 0) und {f400.vehicles} bei {km(f400.dist)} (f = 400). "
                    f"Gleiche Gesamtkosten haben beide bei f* = {R.num(tp)}; ab diesem f ist die Lösung mit weniger Fahrzeugen die billigere. Bei dem gewählten f = {settings.fix} "
                    f"wäre das {'die mit weniger' if settings.fix > tp else 'die mit mehr'} Fahrzeugen.")


def verdict_hebel():
    """Zählung über das Raster: bei welcher Reserve gibt es einen Zielkonflikt."""
    d = R.load()
    fac = d["factors"]
    sep = R.separating_factors()
    parts = []
    for s in C.RESERVE_OPTIONS:
        rc = R.reserve_counts(s)
        parts.append(f"bei {reserve_text(s)} Reserve {rc['front']} von {rc['zellen']}")
    k = R.klass_counts()
    return "info", (f"**Zielkonflikt-Zellen** (ΔV ≥ {R.num(C.FRONT_DV, 1)}) {', '.join(parts)}. Von den {d['n_amp']} Zellen mit 3 oder 5 Ladungen sind {k['front']} Zielkonflikt, "
                    f"{k['keine']} ohne Zielkonflikt (ΔV < {R.num(C.KEINE_DV, 1)}) und {k['zwischen']} Grenzfälle; die Grenzen 0,1 und 0,3 sind gesetzt, nicht hergeleitet. "
                    f"Die Reserve ist der stärkste der vier Faktoren (Zielkonflikt-Anteil {R.pct(fac['s']['0.0']['share'])} bis {R.pct(fac['s']['0.1']['share'])} %, mittleres ΔV {R.num(fac['s']['0.0']['dV_mean'], 2)} bis {R.num(fac['s']['0.1']['dV_mean'], 2)}); "
                    f"Ladungen ({R.pct(fac['k']['3']['share'])} gegen {R.pct(fac['k']['5']['share'])} %) und Kundenzahl ({R.pct(fac['n']['20']['share'])} gegen {R.pct(fac['n']['40']['share'])} %) verschieben den Anteil ebenfalls. "
                    f"Den gesetzten Maßstab „mindestens {R.num(100 * R.SEPARATE_HI, 0)} % Zielkonflikt-Zellen auf einer und höchstens {R.num(100 * R.SEPARATE_LO, 0)} % auf einer anderen Stufe“ "
                    f"{'erfüllt nur der Faktor ' + R.FACTOR_LABEL[sep[0]] if len(sep) == 1 else 'erfüllt kein einzelner Faktor' if not sep else 'erfüllen die Faktoren ' + ', '.join(R.FACTOR_LABEL[f] for f in sep)}; "
                    "die Reserve hat vier, die anderen Faktoren haben zwei Stufen, und der Maßstab wurde wie die Reserve als Hauptfaktor nach einer Erkundung gesetzt.")


def verdict_formel():
    f = R.load()["formel"]
    return "info", (f"**Formel:** Mit a = {R.num(f['a'], 3)} und b = {R.num(f['b'], 3)} (angepasst an {f['n_fit']} Lösungen auf anderen Zufalls-Seeds als die Messung, aber in denselben {len(f['cells'])} Zellen) liegt der mittlere Fehler der "
                    f"vorhergesagten Distanz in {f['n_hold']} von {len(f['cells'])} Zellen bei höchstens {R.num(C.ERR_HOLD, 0)} %, die Spanne ist {R.num(f['err_min'])} bis {R.num(f['err_max'])} % "
                    f"(Reserve {reserve_text(C.FORMEL_RESERVE)}, f = 0, gegen die Lösung der eigenen Suche); {f['n_break']} Zellen erreichen {R.num(10, 0)} % oder mehr. "
                    f"Je Instanz liegt der Fehler im Mittel bei {R.num(f['inst_err_mean'])} %, höchstens bei {R.num(f['inst_err_max'])} %; {f['inst_over10']} von {f['inst_n']} Instanzen erreichen {R.num(10, 0)} % oder mehr.")


def verdict_ortools(own_cost: float, res: dict, secs: int):
    """Vergleich einer OR-Tools-Lösung (Gesamtkosten bei dem gewählten f) mit der eigenen Suche auf dieser Instanz; `res` = {Einstellung: Kosten in Längeneinheiten}."""
    parts = []
    for setting, c in res.items():
        dev = 100.0 * (c - own_cost) / own_cost if own_cost > 0 else 0.0
        parts.append(f"{setting}: {R.num(c, 1)} ({R.num(dev, 2, True)} % gegen die eigene Suche)")
    best = min(res.values())
    kind = "success" if best < own_cost - 1e-9 else "info"
    return kind, (f"**OR-Tools (Gesamtkosten bei dem gewählten f, {secs} s je Einstellung):** " + "; ".join(parts) + f". Eigene Suche: {R.num(own_cost, 1)}. "
                  "Eine Instanz, kein Rang der Löser: OR-Tools bekam {secs} s je Einstellung, die Messreihe nennt die Abweichung über viele Instanzen.")


def verdict_formel_instanz(inst: M.Instance, a_b, points):
    """Formel gegen die gelösten Punkte dieser Instanz; points = [(k, Q, D_gelöst, D_formel)]."""
    errs = [abs(dh - d) / d * 100 for _k, _q, d, dh in points]
    return "info", (f"Auf dieser Instanz weicht die Formel bei den vier Kapazitäten um {', '.join(R.num(e) for e in errs)} % ab (Mittel {R.num(sum(errs) / len(errs))} %); "
                    "eine Instanz streut, die Fehlerkarte der Messreihe zeigt 16 Zellen mit je 25 Instanzen.")
