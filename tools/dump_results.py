"""Verdichtet die Rohdaten der Messreihen (tools/messreihe.py) zu data/fgr_results.json (Aggregate, unter 150 kB; die Rohdaten liegen nicht im Repo).

Aufruf:  python tools/dump_results.py [--src ORDNER] [--out data/fgr_results.json]

Alle Zahlen der App und der README stammen aus dieser Datei; tests/test_claims.py rechnet sie nach. Fehlt eine Rohdatei, bricht das Skript ab
(keine halben Dateien). Die Abschnitte unter "vormessung" sind nicht neu gerechnet: sie stammen aus tourenplanung-planung/messreihe_flotte/ERGEBNIS.md
und messreihe_flotte_ap0/ERGEBNIS.md und wurden mit dem früheren Packungsstart (CP-SAT) gemessen."""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import fgr_model as M  # noqa: E402
import fgr_search as S  # noqa: E402
from fgr_formula import fit_ab  # noqa: E402

FS = S.FS
SCALE = M.SCALE
AREA = (100.0 * SCALE) ** 2
FRONT_DV, KEINE_DV = 0.3, 0.1                 # Grenzen der Zellenklassen (gesetzt, nicht hergeleitet)
RESERVES = (0.0, 0.02, 0.05, 0.10)
SIGMAS = (0.4, 0.5, 1.0, 1.5, 2.0)
QFS = (25, 50, 100, 200)


def load(path):
    return [json.loads(line) for line in Path(path).open(encoding="utf-8") if line.strip()]


def mean(xs):
    xs = list(xs)
    return statistics.mean(xs) if xs else None


def quartiles(xs):
    xs = sorted(xs)
    if len(xs) < 2:
        return None
    return [round(q, 4) for q in statistics.quantiles(xs, n=4, method="inclusive")]


def first_drop(r):
    """Index der ersten Fixkostenstufe, bei der die Fahrzeugzahl unter die bei f = 0 sinkt, sonst None."""
    return next((i for i, v in enumerate(r["V"]) if v < r["V"][0]), None)


def pair_fstar(r):
    """Rechnerischer Kipppunkt der Lösungen bei f = 0 und f = 400: (D₄₀₀ − D₀) / (V₀ − V₄₀₀) in Längeneinheiten je Fahrzeug, nicht unter 0 (Instanzen mit weniger Fahrzeugen)."""
    return max(0.0, (r["D"][-1] - r["D"][0]) / SCALE / (r["V"][0] - r["V"][-1]))


def klass(dv):
    return "front" if dv >= FRONT_DV else ("keine" if dv < KEINE_DV else "zwischen")


# ------------------------------------------------------------------------------------------------ Hauptraster

def cells_of(rows):
    by = defaultdict(list)
    for r in rows:
        by[(r["n"], r["depot"], r["k"], r["s"])].append(r)
    cells = []
    for (n, depot, k, s), rs in sorted(by.items()):
        fstar_counts = {str(f): 0 for f in FS[1:]}
        fstar = []
        price = []
        pair = []
        for r in rs:
            idx = first_drop(r)
            if idx is not None:
                fstar_counts[str(r["f"][idx])] += 1
                fstar.append(r["f"][idx])
            if r["V"][-1] < r["V"][0]:
                price.append((r["D"][-1] / r["D"][0] - 1) * 100)
                pair.append(pair_fstar(r))
        dv = mean(r["V"][0] - r["V"][-1] for r in rs)
        cells.append({
            "n": n, "depot": depot, "k": k, "s": s, "m": len(rs), "ampel": k in (3, 5), "dV": dv, "klass": klass(dv),
            "n_front_inst": len(price), "share_front_inst": len(price) / len(rs), "n_fstar": len(fstar), "fstar_counts": fstar_counts,
            "fpair_median": statistics.median(pair) if pair else None, "fpair_quartiles": quartiles(pair),
            "n_same_dist": sum(1 for r in rs if r["V"][-1] < r["V"][0] and r["D"][-1] <= r["D"][0]), "n_v400_at_bound": sum(1 for r in rs if r["V"][-1] == r["vmin"]),
            "n_less_at_f": {str(f): sum(1 for r in rs if r["V"][i] < r["V"][0]) for i, f in enumerate(FS) if f > 0},
            "fstar_median": statistics.median(fstar) if fstar else None, "price_front_inst": mean(price) if price else None,
            "dD_all": mean((r["D"][-1] / r["D"][0] - 1) * 100 for r in rs),
            "V0": mean(r["V"][0] for r in rs), "Vend": mean(r["V"][-1] for r in rs), "vmin": mean(r["vmin"] for r in rs),
            "excess0": mean(r["V"][0] - r["vmin"] for r in rs), "vmin_hit_end": mean(1 if r["V"][-1] == r["vmin"] else 0 for r in rs),
            "max_distinct_V": max(len(set(r["V"])) for r in rs),
            "Vf": [mean(r["V"][i] for r in rs) for i in range(len(FS))], "Df": [mean(r["D"][i] for r in rs) for i in range(len(FS))],
            "Q": mean(r["Q"] for r in rs), "t_mean": mean(r["t"] for r in rs),
        })
    for ci, c in enumerate(cells, start=1):
        c["ci"] = ci
    return cells


def by_reserve(rows):
    """Zeilen mit k in {3, 5} je Reserve: Zählungen über Instanzen (100 je Reserve und k, 200 je Reserve)."""
    out = {}
    for s in RESERVES:
        rs = [r for r in rows if r["k"] in (3, 5) and r["s"] == s]
        drop = [r for r in rs if r["V"][-1] < r["V"][0]]
        fstar = [r["f"][first_drop(r)] for r in drop]
        price = [(r["D"][-1] / r["D"][0] - 1) * 100 for r in drop]
        pair = [pair_fstar(r) for r in drop]
        per_k = {}
        for k in (3, 5):
            sub = [r for r in rs if r["k"] == k]
            d_ = [r for r in sub if r["V"][-1] < r["V"][0]]
            per_k[str(k)] = {"m": len(sub), "n_front_inst": len(d_), "dV": mean(r["V"][0] - r["V"][-1] for r in sub),
                             "dD_all": mean((r["D"][-1] / r["D"][0] - 1) * 100 for r in sub),
                             "fstar_counts": {str(f): sum(1 for r in d_ if r["f"][first_drop(r)] == f) for f in FS[1:]}}
        out[str(s)] = {
            "m": len(rs), "n_front_inst": len(drop), "excess0": mean(r["V"][0] - r["vmin"] for r in rs),
            "fstar_median": statistics.median(fstar) if fstar else None, "fstar_quartiles": quartiles(fstar), "n_fstar": len(fstar),
            "price_mean": mean(price) if price else None, "per_k": per_k,
            "fpair_median": statistics.median(pair) if pair else None, "fpair_quartiles": quartiles(pair),
            "n_same_dist": sum(1 for r in drop if r["D"][-1] <= r["D"][0]),
            "dV_mean": mean(r["V"][0] - r["V"][-1] for r in rs),
            "Vf_excess": [mean(r["V"][i] - r["vmin"] for r in rs) for i in range(len(FS))],
            "max_distinct_V": max(len(set(r["V"])) for r in rs),
            "dV_nonincreasing_mean": all(mean(r["V"][i] for r in rs) >= mean(r["V"][i + 1] for r in rs) - 1e-9 for i in range(len(FS) - 1)),
        }
    return out


def factors(cells):
    amp = [c for c in cells if c["ampel"]]
    out = {}
    for fac in ("s", "k", "n", "depot"):
        g = defaultdict(list)
        for c in amp:
            g[str(c[fac])].append(c)
        out[fac] = {lvl: {"cells": len(v), "front": sum(1 for c in v if c["klass"] == "front"), "share": sum(1 for c in v if c["klass"] == "front") / len(v),
                          "dV_mean": mean(c["dV"] for c in v)} for lvl, v in sorted(g.items())}
    return out


# ------------------------------------------------------------------------------------------------ Formel

def formula_part(rows, fit_rows):
    fr = [(r["D"][0], 2.0 * r["rbar"] * r["S"] / r["Q"], math.sqrt(r["n"] * AREA)) for r in fit_rows]
    a, b = fit_ab(fr)
    errs_fit = [abs(a * x1 + b * x2 - D) / D * 100 for D, x1, x2 in fr]
    by = defaultdict(list)
    for r in rows:
        if r["s"] == 0.10 and r["k"] in (2, 3, 5, 8):
            by[(r["n"], r["depot"], r["k"])].append(r)
    cells = []
    all_abs = []
    for (n, depot, k), rs in sorted(by.items()):
        errs = []
        for r in rs:
            dh = a * 2.0 * r["rbar"] * r["S"] / r["Q"] + b * math.sqrt(r["n"] * AREA)
            errs.append((dh - r["D"][0]) / r["D"][0] * 100)
        all_abs.extend(abs(e) for e in errs)
        cells.append({"n": n, "depot": depot, "k": k, "m": len(rs), "err_mean": mean(abs(e) for e in errs), "bias": mean(errs)})
    return {"a": a, "b": b, "n_fit": len(fit_rows), "err_fit_mean": mean(errs_fit), "err_fit_max": max(errs_fit),
            "n_hold": sum(1 for c in cells if c["err_mean"] <= 5.0), "n_break": sum(1 for c in cells if c["err_mean"] >= 10.0),
            "err_mean_all": mean(c["err_mean"] for c in cells), "err_min": min(c["err_mean"] for c in cells),
            "inst_n": len(all_abs), "inst_err_mean": mean(all_abs), "inst_err_max": max(all_abs), "inst_over10": sum(1 for e in all_abs if e >= 10.0),
            "bias_min": min(c["bias"] for c in cells), "bias_max": max(c["bias"] for c in cells),
            "err_max": max(c["err_mean"] for c in cells), "cells": cells}


def qstern(rows, a, b):
    """Größenwahl: Kostenfamilie q^σ (Fixkosten und Kilometerkosten je Fahrzeug mit q = Q / Q_ref, Q_ref = Q bei k = 2), Reserve 10 %."""
    data = defaultdict(dict)
    for r in rows:
        if r["s"] == 0.10 and r["k"] in (2, 3, 5, 8):
            data[(r["n"], r["depot"], r["seed"])][r["k"]] = r
    KS = (2, 3, 5, 8)
    out = []
    for sg in SIGMAS:
        for f in QFS:
            fi = FS.index(f)
            cases = inner = hit_all = hit_inner = near = 0
            true_cnt = {k: 0 for k in KS}
            pred_cnt = {k: 0 for k in KS}
            for (n, depot, seed), d in sorted(data.items()):
                if set(d) != set(KS):
                    continue
                qref = d[2]["Q"]
                true, pred = {}, {}
                for k in KS:
                    r = d[k]
                    q = (r["Q"] / qref) ** sg
                    true[k] = q * (f * SCALE * r["V"][fi] + r["D"][fi])
                    vh = math.ceil(r["S"] / r["Q"])
                    dh = a * 2.0 * r["rbar"] * r["S"] / r["Q"] + b * math.sqrt(r["n"] * AREA)
                    pred[k] = q * (f * SCALE * vh + dh)
                kt = min(KS, key=lambda k: (true[k], k))
                kp = min(KS, key=lambda k: (pred[k], k))
                cases += 1
                true_cnt[kt] += 1
                pred_cnt[kp] += 1
                is_inner = kt in (3, 5)
                inner += is_inner
                hit_all += kt == kp
                hit_inner += is_inner and kt == kp
                near += abs(KS.index(kt) - KS.index(kp)) <= 1
            out.append({"sigma": sg, "f": f, "cases": cases, "inner": inner, "hit_all": hit_all, "hit_inner": hit_inner, "near": near,
                        "const_hit": max(true_cnt.values()), "true_cnt": {str(k): v for k, v in true_cnt.items()}, "pred_cnt": {str(k): v for k, v in pred_cnt.items()}})
    return out


# ------------------------------------------------------------------------------------------------ OR-Tools, Orakel, Mengen

def ort_part(rows, ort):
    own = {}
    for r in rows:
        for i, f in enumerate(r["f"]):
            own[(r["n"], r["depot"], r["k"], r["s"], r["seed"], f)] = r["cost"][i]
    g = defaultdict(list)
    best = defaultdict(dict)
    by_s = defaultdict(list)
    errs = 0
    secs = defaultdict(list)
    for o in ort:
        if o.get("cost") is None:
            continue
        errs += len(o.get("errs") or [])
        key = (o["n"], o["depot"], o["k"], o["s"], o["seed"], o["f"])
        e = own.get(key)
        if e is None:
            continue
        dev = (o["cost"] - e) / e * 100
        g[(o["setting"], o["n"])].append(dev)
        by_s[(o["setting"], o["s"])].append(dev)
        best[key][o["setting"]] = o["cost"]
        secs[o["n"]].append(o["secs"])
    vals, vals35 = [], []
    for key, d in best.items():
        e = own[key]
        v = (min(d.values()) - e) / e * 100
        vals.append(v)
        if key[2] in (3, 5):
            vals35.append(v)
    own_stage = {str(n): mean(r["t"] / len(FS) for r in rows if r["n"] == n) for n in (20, 40)}
    return {
        "runs": len(ort), "n_infeasible": sum(1 for o in ort if o.get("cost") is None), "n_error": errs,
        "by_setting_n": {f"{st}|{n}": {"mean": mean(v), "runs": len(v), "better": sum(1 for x in v if x < -1e-9), "max": max(v)} for (st, n), v in sorted(g.items())},
        "by_setting_reserve": {f"{st}|{s}": {"mean": mean(v), "runs": len(v)} for (st, s), v in sorted(by_s.items())},
        "best_of_two": {"mean": mean(vals), "runs": len(vals), "better": sum(1 for x in vals if x < -1e-9), "max": max(vals), "median": statistics.median(vals),
                        "equal": sum(1 for x in vals if abs(x) < 1e-9), "over1": sum(1 for x in vals if x > 1.0), "over5": sum(1 for x in vals if x > 5.0)},
        "best_of_two_k35": {"mean": mean(vals35), "runs": len(vals35), "better": sum(1 for x in vals35 if x < -1e-9)},
        "secs_ort": {str(n): mean(v) for n, v in secs.items()}, "own_secs_per_stage": own_stage,
    }


def orakel_part(orakel):
    out = {}
    all_rows = [r for o in orakel for r in o["rows"]]
    for s in (0.0, 0.02, 0.10):
        rs = [r for r in all_rows if r["s"] == s]
        gaps = [(r["val"] - r["opt"]) / r["opt"] * 100 for r in rs]
        live = [(r["val_live"] - r["opt"]) / r["opt"] * 100 for r in rs if "val_live" in r]
        p1 = [(r["val_pass1"] - r["opt"]) / r["opt"] * 100 for r in rs]
        c48 = [(r["val"] - r["opt"]) / r["opt"] * 100 for r in rs if "val_live" in r]
        p48 = [(r["val_pass1"] - r["opt"]) / r["opt"] * 100 for r in rs if "val_live" in r]
        inst_over = {(r["depot"], r["seed"]) for r in rs if (r["val"] - r["opt"]) / r["opt"] * 100 > 0.5}
        inst_over_p1 = {(r["depot"], r["seed"]) for r in rs if (r["val_pass1"] - r["opt"]) / r["opt"] * 100 > 0.5}
        inst_all = {(r["depot"], r["seed"]) for r in rs}
        out[str(s)] = {"cases": len(rs), "gap_mean": mean(gaps), "gap_max": max(gaps), "n_over_half": sum(1 for g in gaps if g > 0.5),
                       "n_optimal": sum(1 for g in gaps if g <= 1e-9), "n_below": sum(1 for g in gaps if g < -1e-9),
                       "live_cases": len(live), "live_gap_mean": mean(live) if live else None, "live_gap_max": max(live) if live else None,
                       "chain48_gap_mean": mean(c48), "pass148_gap_mean": mean(p48),
                       "live_n_over_half": sum(1 for r in rs if "val_live" in r and (r["val_live"] - r["opt"]) / r["opt"] * 100 > 0.5),
                       "instances": len(inst_all), "instances_over_half": len(inst_over), "pass1_instances_over_half": len(inst_over_p1),
                       "pass1_gap_mean": mean(p1), "pass1_gap_max": max(p1), "pass1_n_over_half": sum(1 for g in p1 if g > 0.5), "pass1_n_optimal": sum(1 for g in p1 if g <= 1e-9)}
    gaps = [(r["val"] - r["opt"]) / r["opt"] * 100 for r in all_rows]
    out["all"] = {"cases": len(all_rows), "gap_mean": mean(gaps), "gap_max": max(gaps), "n_over_half": sum(1 for g in gaps if g > 0.5)}
    return out


def mengen_part(rows):
    out = {}
    for dist in sorted({r["dist"] for r in rows}):
        per = {}
        for s in RESERVES:
            by = defaultdict(list)
            for r in rows:
                if r["dist"] == dist and r["s"] == s:
                    by[(r["n"], r["depot"], r["k"])].append(r)
            cells = []
            for key, rs in sorted(by.items()):
                dv = mean(r["V"][0] - r["V"][-1] for r in rs)
                cells.append({"dV": dv, "n_front_inst": sum(1 for r in rs if r["V"][-1] < r["V"][0]), "m": len(rs)})
            allr = [r for rs in by.values() for r in rs]
            drop = [r for r in allr if r["V"][-1] < r["V"][0]]
            per[str(s)] = {
                "cells": len(cells), "front_cells": sum(1 for c in cells if c["dV"] >= FRONT_DV), "front_cell_inst": sorted(c["n_front_inst"] for c in cells if c["dV"] >= FRONT_DV),
                "dV_mean": mean(c["dV"] for c in cells),
                "m": len(allr), "n_front_inst": len(drop), "price": mean((r["D"][-1] / r["D"][0] - 1) * 100 for r in drop) if drop else None,
                "qmax_bindet": sum(1 for r in allr if r["qmax_bindet"]),
            }
        out[dist] = per
    return out


# ------------------------------------------------------------------------------------------------ Ausgabe

VORMESSUNG = {
    "quelle": "tourenplanung-planung/messreihe_flotte/ERGEBNIS.md und messreihe_flotte_ap0/ERGEBNIS.md (Messung 2026-11-18, Packungsstart mit CP-SAT; nicht neu gerechnet)",
    "abstimmung_400_gegen_1500": {"laeufe": 36, "mehrkosten_mittel": 0.22, "mehrkosten_max": 2.66},
    "kontrolle_1500": {"zellen": 16, "instanzen_je_zelle": 3, "werte": 336, "fahrzeugzahl_verschieden": 4, "mehrkosten_mittel": 0.065, "mehrkosten_max": 4.70,
                       "front_zellen_400": 11, "front_zellen_1500": 11},
    "kontrolle_2000": {"zellen": 16, "instanzen_je_zelle": 10, "faelle": 640, "fahrzeugzahl_verschieden": 6, "klassenwechsel": 2, "dV_400": 0.438, "dV_2000": 0.431},
    "plattform": {"zeilen": 12, "identisch": 11, "ursache": "CP-SAT-Packungsstart fand auf Windows und Linux verschiedene Packungen"},
    "erkundung": {"seeds": [100000, 100004], "iterationen": 150, "n": [20, 40], "depot": "rand"},
    "haupt": {"n_front": 9, "n_keine": 19, "n_zwischen": 4, "front_je_reserve": [7, 2, 0, 0], "excess0_je_reserve": [0.69, 0.23, 0.04, 0.01],
              "n_front_inst_je_reserve": [129, 46, 7, 2], "fstar_median_reserve_0": 50, "price_je_reserve": [5.3, 2.5, 2.0, 1.0], "max_distinct_V": 2, "max_dV": 0.92},
    "formel": {"a": 0.9390, "b": 0.6266, "err_fit_mean": 3.99, "err_fit_max": 18.8, "n_hold": 14, "err_min": 1.80, "err_max": 5.33, "err_mean_all": 3.69},
    "ort": {"best_of_two_mean": 0.61, "better": 11, "runs": 800, "max": 21.2, "neue_ort_gegen_alte_suche_mean": 0.514, "neue_ort_gegen_alte_suche_better": 11},
    "mix_n12": {"sigma": 1.0, "paar": [8, 3], "f": 100, "instanzen": 24, "gegen_beste_einheitsflotte": 0.24, "gegen_bessere_des_paares": 1.75},
    "orakel_n12": {"reserve_0": {"faelle": 112, "mittel": 0.267, "ueber_halb": 15, "max": 6.85}, "reserve_2": {"mittel": 0.010}, "reserve_10": {"mittel": 0.000}},
}


def build(src):
    src = Path(src)
    rows = load(src / "sweep_m1.jsonl")
    fit_rows = load(src / "sweep_fit.jsonl")
    ort = load(src / "sweep_ort.jsonl")
    orakel = load(src / "sweep_orakel.jsonl")
    mengen = load(src / "sweep_mengen.jsonl")
    cells = cells_of(rows)
    formel = formula_part(rows, fit_rows)
    amp = [c for c in cells if c["ampel"]]
    return {
        "meta": {"iters": 400, "fs": list(FS), "seeds_m1": [300000, 300024], "seeds_fit": [1000, 1011], "rows_m1": len(rows), "rows_fit": len(fit_rows),
                 "orakel_seeds": [2000, 2007], "mengen_seeds": [310000, 310007], "grenzen": {"front_dV": FRONT_DV, "keine_dV": KEINE_DV},
                 "t_m1_summe_s": sum(r["t"] for r in rows), "n_v400_at_bound": sum(1 for r in rows if r["V"][-1] == r["vmin"])},
        "cells": cells,
        "n_amp": len(amp), "n_front": sum(1 for c in amp if c["klass"] == "front"), "n_keine": sum(1 for c in amp if c["klass"] == "keine"),
        "n_zwischen": sum(1 for c in amp if c["klass"] == "zwischen"),
        "by_reserve": by_reserve(rows), "factors": factors(cells),
        "formel": formel, "qstern": qstern(rows, formel["a"], formel["b"]),
        "ort": ort_part(rows, ort), "orakel": orakel_part(orakel), "mengen": mengen_part(mengen),
        "vormessung": VORMESSUNG,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=str(ROOT.parent / "tourenplanung-planung" / "messreihe_fgr"))
    ap.add_argument("--out", default=str(ROOT / "data" / "fgr_results.json"))
    args = ap.parse_args()
    res = build(args.src)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    print(f"{out}: {out.stat().st_size / 1024:.0f} kB, {len(res['cells'])} Zellen, Front {res['n_front']}, keine {res['n_keine']}, dazwischen {res['n_zwischen']}")
