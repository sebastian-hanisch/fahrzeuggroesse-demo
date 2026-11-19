"""Prüft für jedes Preset, ob sein Zufalls-Seed (ab 500000, nie 1000 bis 1011, 2000 bis 2007, 300000 bis 300024 und 310000 bis 310007 der Messreihen) die Geschichte des Presets auf dem Lauf
zeigt, und sucht sonst den nächsten Seed ab 500000, bei dem das Kriterium aus fgr_stories.py erfüllt ist.

Aufruf:  python tools/find_preset_seeds.py            (gibt je Preset Seed, Geschichte und die Kennzahlen des Laufs aus)
         python tools/find_preset_seeds.py --suche    (sucht für Presets, deren Seed die Geschichte nicht zeigt, den nächsten passenden Seed; mehrere Prozesse)
"""
import pathlib
import sys
from concurrent.futures import ProcessPoolExecutor

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import fgr_constants as C  # noqa: E402
import fgr_evaluation as E  # noqa: E402
import fgr_stories as S  # noqa: E402


def settings(name, seed=None):
    p = C.PRESETS[name]
    return E.Settings(p["n"], p["depot"], p["k"], p["reserve"], p["fix"], p["ils"], p["seed"] if seed is None else seed)


def check(args):
    name, seed = args
    st = settings(name, seed)
    a = E.analyse(st)
    f0, sel, f400 = (E.sol_of(a, k) for k in ("f0", "sel", "f400"))
    tp = E.tipping_point(f0, f400)
    return seed, S.STORIES[name](a, st), (f0.vehicles, sel.vehicles, f400.vehicles), (f0.dist, sel.dist, f400.dist), tp


def main():
    suche = "--suche" in sys.argv
    with ProcessPoolExecutor(max_workers=6) as ex:
        for name in C.PRESETS:
            seed, ok, v, d, tp = check((name, settings(name).seed))
            print(f"{name}: Seed {seed}, Geschichte {'ja' if ok else 'NEIN'}; Fahrzeuge f0/gewählt/f400 {v}, Distanz {tuple(round(x / 10, 1) for x in d)}, Kipppunkt {None if tp is None else round(tp, 1)}")
            if not ok and suche:
                seeds = [(name, s) for s in range(500000, 500060)]
                for s, ok2, v2, d2, tp2 in ex.map(check, seeds):
                    if ok2:
                        print(f"   -> passender Seed: {s} (Fahrzeuge {v2}, Distanz {tuple(round(x / 10, 1) for x in d2)}, Kipppunkt {None if tp2 is None else round(tp2, 1)})")
                        break


if __name__ == "__main__":
    main()
