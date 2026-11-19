"""Messreihen der Demo (laufen Stunden; Rohdaten liegen NICHT im Repo, `tools/dump_results.py` verdichtet sie zu data/fgr_results.json).

Aufruf (aus dem Repo-Ordner):  python tools/messreihe.py <art> [--out ORDNER] [--procs 6]

Arten (jede schreibt Zeilen nach <out>/sweep_<art>.jsonl; ein Abbruch ist folgenlos: beim nächsten Aufruf werden nur fehlende Schlüssel gerechnet,
die Aufträge sind deterministisch):
  m1      Hauptraster: 40 Zellen (n 20/40 · Depot Rand/Mitte · 10 Kapazitäten) · 25 Instanzen (Zufalls-Seeds 300000 bis 300024) · 7 Fixkostenstufen
  fit     Anpassung der Formel: 192 Lösungen bei f = 0, Reserve 10 % (Zufalls-Seeds 1000 bis 1011)
  ort     OR-Tools mit Fixkosten (beide Einstellungen) auf den ersten 5 Instanzen je Zelle, f in {0, 25, 100, 400}
  orakel  n = 12 gegen das exakte Verfahren (Zufalls-Seeds 2000 bis 2007)
  mengen  andere Mengenverteilungen (Zufalls-Seeds 310000 bis 310007), 4 Fixkostenstufen
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import fgr_model as M  # noqa: E402
import fgr_search as S  # noqa: E402
import fgr_solvers as V  # noqa: E402

SEEDS_M1 = list(range(300000, 300025))
SEEDS_FIT = list(range(1000, 1012))
SEEDS_ORAKEL = list(range(2000, 2008))
SEEDS_MENGEN = list(range(310000, 310008))
ITERS = 400
CAPS = [(k, s) for k in (3, 5) for s in (0.0, 0.02, 0.05, 0.10)] + [(2, 0.10), (8, 0.10)]      # (Ladungen k, Reserve s)
FS_MENGEN = (0, 25, 100, 400)
DISTS = ("gleich", "weit", "schief", "fast")


def key_of(d, kind):
    if kind in ("m1", "fit"):
        return f"{d['n']}|{d['depot']}|{d['k']}|{d['s']}|{d['seed']}"
    if kind == "ort":
        return f"{d['n']}|{d['depot']}|{d['k']}|{d['s']}|{d['seed']}|{d['f']}|{d['setting']}"
    if kind == "orakel":
        return f"{d['depot']}|{d['s']}|{d['seed']}"
    return f"{d['n']}|{d['depot']}|{d['k']}|{d['s']}|{d['dist']}|{d['seed']}"


def jobs(kind):
    out = []
    if kind == "m1":
        for n in (20, 40):
            for depot in ("rand", "mitte"):
                for k, s in CAPS:
                    for seed in SEEDS_M1:
                        out.append({"n": n, "depot": depot, "k": k, "s": s, "seed": seed})
    elif kind == "fit":
        for n in (20, 40):
            for depot in ("rand", "mitte"):
                for k in (2, 3, 5, 8):
                    for seed in SEEDS_FIT:
                        out.append({"n": n, "depot": depot, "k": k, "s": 0.10, "seed": seed})
    elif kind == "ort":
        for n in (20, 40):
            for depot in ("rand", "mitte"):
                for k, s in CAPS:
                    for f in (0, 25, 100, 400):
                        for seed in SEEDS_M1[:5]:
                            for st in V.SETTINGS:
                                out.append({"n": n, "depot": depot, "k": k, "s": s, "seed": seed, "f": f, "setting": st, "secs": 3 if n == 20 else 6})
    elif kind == "orakel":
        for depot in ("rand", "mitte"):
            for s in (0.0, 0.02, 0.10):
                for seed in SEEDS_ORAKEL:
                    out.append({"depot": depot, "s": s, "seed": seed})
    elif kind == "mengen":
        for n in (20, 40):
            for depot in ("rand", "mitte"):
                for k in (3, 5):
                    for s in (0.0, 0.02, 0.05, 0.10):
                        for dist in DISTS:
                            for seed in SEEDS_MENGEN:
                                out.append({"n": n, "depot": depot, "k": k, "s": s, "dist": dist, "seed": seed})
    return out


# ------------------------------------------------------------------------------------------------ Aufträge (Modulebene für ProcessPoolExecutor)

def _row_base(inst, a):
    return {"n": a["n"], "depot": a["depot"], "k": a["k"], "s": a["s"], "seed": a["seed"], "Q": inst.Q, "S": sum(inst.dem),
            "rbar": M.depot_dist_mean(inst), "vmin": M.lower_bound_vehicles(inst)}


def job_m1(a):
    inst = M.make_instance(a["n"], a["depot"], a["seed"], a["k"], a["s"])
    out = _row_base(inst, a)
    t0 = time.time()
    sols = S.chain(inst, S.FS, ITERS, a["seed"])
    out["f"], out["V"], out["D"], out["cost"] = [], [], [], []
    for f in S.FS:
        r = sols[f]
        assert not M.verify(inst, r)
        out["f"].append(f)
        out["V"].append(len(r))
        out["D"].append(M.distance_of(inst, r))
        out["cost"].append(M.total_cost(inst, r, f * M.SCALE))
    out["t"] = time.time() - t0
    return out


def job_fit(a):
    inst = M.make_instance(a["n"], a["depot"], a["seed"], a["k"], a["s"])
    out = _row_base(inst, a)
    t0 = time.time()
    sols = S.chain(inst, (0,), ITERS, a["seed"])
    out["D"] = [M.distance_of(inst, sols[0])]
    out["V"] = [len(sols[0])]
    out["t"] = time.time() - t0
    return out


def job_ort(a):
    inst = M.make_instance(a["n"], a["depot"], a["seed"], a["k"], a["s"])
    t0 = time.time()
    routes, _obj = V.solve_ortools(inst, a["f"] * M.SCALE, a["secs"], a["setting"])
    res = {k: a[k] for k in ("n", "depot", "k", "s", "seed", "f", "setting", "secs")}
    if routes is None:
        res["cost"] = None
    else:
        res["cost"] = M.total_cost(inst, routes, a["f"] * M.SCALE)
        res["V"] = len(routes)
        res["D"] = M.distance_of(inst, routes)
        res["errs"] = M.verify(inst, routes)
    res["t"] = time.time() - t0
    return res


def job_orakel(a):
    inst = M.make_instance(12, a["depot"], a["seed"], 3, a["s"])
    opts = V.exact_optima(inst, [f * M.SCALE for f in S.FS])
    sols = S.chain(inst, S.FS, ITERS, a["seed"])                                 # wie im Hauptraster
    short = S.short_chain(inst, (0, 100, 400), ITERS, a["seed"])                  # wie die Live-Rechnung der App
    pass1 = S.short_chain(inst, S.FS, ITERS, a["seed"])                           # ein Durchgang über alle sieben Stufen (so rechnete die Vormessung die Front-Treue)
    rows = []
    for f in S.FS:
        opt = opts[f * M.SCALE]
        val = M.total_cost(inst, sols[f], f * M.SCALE)
        row = {"depot": a["depot"], "s": a["s"], "seed": a["seed"], "f": f, "opt": opt, "val": val, "V": len(sols[f]), "val_pass1": M.total_cost(inst, pass1[f], f * M.SCALE)}
        if f in short:
            row["val_live"] = M.total_cost(inst, short[f], f * M.SCALE)
        rows.append(row)
    return {"depot": a["depot"], "s": a["s"], "seed": a["seed"], "rows": rows}


def _demand(rd, dist):
    if dist == "gleich":
        return 5 + rd.below(21)
    if dist == "weit":
        return 1 + rd.below(40)
    if dist == "fast":
        return 14 + rd.below(3)
    if dist == "schief":                            # 80 % gleichverteilt 3 bis 10, 20 % gleichverteilt 25 bis 45
        a = rd.below(100)
        b = rd.below(1008)                          # 1008 = 8 * 126 = 21 * 48: beide Reste gleichverteilt
        return 3 + (b % 8) if a < 80 else 25 + (b % 21)
    raise ValueError(dist)


def make_base_dist(n, depot, seed, dist):
    """Orte wie M.make_base, Mengen nach Verteilung `dist`."""
    from fgr_rng import SplitMix64
    rx, rd = SplitMix64(seed * 8 + 1), SplitMix64(seed * 8 + 2)
    xy, dem = [M.DEPOTS[depot]], [0]
    for _ in range(n):
        u1, u2 = rx.uniform(), rx.uniform()
        xy.append((M.AREA_SIDE * u1, M.AREA_SIDE * u2))
        dem.append(_demand(rd, dist))
    return M.Instance(n, dem, sum(dem), xy, M.dist_matrix(xy), {})


def job_mengen(a):
    base = make_base_dist(a["n"], a["depot"], a["seed"], a["dist"])
    inst = M.with_capacity(base, M.capacity(base.dem, a["k"], a["s"]))
    out = _row_base(inst, a)
    out["dist"] = a["dist"]
    out["qmax_bindet"] = inst.Q == max(inst.dem[1:])
    t0 = time.time()
    sols = S.chain(inst, FS_MENGEN, ITERS, a["seed"])
    out["f"], out["V"], out["D"], out["cost"] = [], [], [], []
    for f in FS_MENGEN:
        r = sols[f]
        assert not M.verify(inst, r)
        out["f"].append(f)
        out["V"].append(len(r))
        out["D"].append(M.distance_of(inst, r))
        out["cost"].append(M.total_cost(inst, r, f * M.SCALE))
    out["t"] = time.time() - t0
    return out


FN = {"m1": job_m1, "fit": job_fit, "ort": job_ort, "orakel": job_orakel, "mengen": job_mengen}


def run(kind, out_dir, workers):
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"sweep_{kind}.jsonl"
    done = set()
    if path.exists():
        for line in path.open(encoding="utf-8"):
            if line.strip():
                done.add(key_of(json.loads(line), kind))
    todo = [j for j in jobs(kind) if key_of(j, kind) not in done]
    print(f"[{kind}] {len(done)} fertig, {len(todo)} offen, {workers} Prozesse", flush=True)
    t0 = time.time()
    n_done = 0
    with ProcessPoolExecutor(max_workers=workers) as ex, path.open("a", encoding="utf-8") as fh:
        for res in ex.map(FN[kind], todo, chunksize=1):
            fh.write(json.dumps(res) + "\n")
            fh.flush()
            n_done += 1
            if n_done % 25 == 0 or n_done == len(todo):
                print(f"[{kind}] {n_done}/{len(todo)} nach {time.time() - t0:.0f} s", flush=True)
    print(f"[{kind}] fertig nach {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("art", choices=sorted(FN))
    ap.add_argument("--out", default=str(ROOT.parent / "tourenplanung-planung" / "messreihe_fgr"))
    ap.add_argument("--procs", type=int, default=6)
    args = ap.parse_args()
    run(args.art, Path(args.out), args.procs)
