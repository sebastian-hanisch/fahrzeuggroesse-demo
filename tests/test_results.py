"""Ergebnisdatei data/fgr_results.json: Aufbau, innere Widerspruchsfreiheit und die Zuordnung Einstellung → Zelle (die Zahlen der README stehen in test_claims.py)."""

import itertools

import pytest

import fgr_constants as C
import fgr_results as R

DATA = R.load()


def test_vierzig_zellen_davon_zweiunddreissig_ampel_zellen_und_jede_einstellung_hat_eine_zelle():
    assert len(DATA["cells"]) == 40 and len(R.cells()) == 32 == DATA["n_amp"]
    for n, depot, k, s in itertools.product(C.N_OPTIONS, C.DEPOT_OPTIONS, C.K_OPTIONS, C.RESERVE_OPTIONS):
        c = R.cell_of(n, depot, k, s)
        assert (c["n"], c["depot"], c["k"]) == (n, depot, k) and c["s"] == pytest.approx(s) and c["ampel"] and c["m"] == 25


def test_unbekannte_einstellung_wirft():
    with pytest.raises(KeyError):
        R.cell_of(30, "rand", 5, 0.0)


def test_zellen_sind_in_sich_widerspruchsfrei():
    for c in DATA["cells"]:
        assert c["dV"] == pytest.approx(c["Vf"][0] - c["Vf"][-1])                        # Mittel der Differenzen = Differenz der Mittel
        assert c["klass"] == ("front" if c["dV"] >= C.FRONT_DV else "keine" if c["dV"] < C.KEINE_DV else "zwischen")
        assert c["n_front_inst"] == c["n_less_at_f"]["400"] <= c["m"]
        assert c["n_fstar"] >= c["n_front_inst"] and sum(c["fstar_counts"].values()) == c["n_fstar"]
        assert all(c["Vf"][i] >= c["Vf"][i + 1] - 1e-9 for i in range(6))                  # V im Mittel nicht steigend über f
        assert c["vmin"] <= c["Vend"] <= c["V0"] + 1e-9 and c["excess0"] >= -1e-9
        assert c["max_distinct_V"] <= 3
        assert (c["price_front_inst"] is None) == (c["n_front_inst"] == 0)
        assert c["Df"][0] <= c["Df"][-1] * (1 + 0.02)                                       # die Distanz bei f = 400 ist im Mittel nicht kürzer als die bei f = 0 (Suchrauschen bis 2 %)


def test_zaehlungen_der_klassen_stimmen_mit_den_zellen_ueberein():
    amp = R.cells()
    assert DATA["n_front"] == sum(c["klass"] == "front" for c in amp) and DATA["n_keine"] == sum(c["klass"] == "keine" for c in amp)
    assert DATA["n_front"] + DATA["n_keine"] + DATA["n_zwischen"] == 32 == sum(R.klass_counts().values())
    assert sum(R.reserve_counts(s)["front"] for s in C.RESERVE_OPTIONS) == DATA["n_front"]
    assert all(R.reserve_counts(s)["zellen"] == 8 for s in C.RESERVE_OPTIONS)


def test_zaehlungen_je_reserve_stimmen_mit_den_zellen_ueberein():
    for s in C.RESERVE_OPTIONS:
        cells = [c for c in R.cells() if c["s"] == pytest.approx(s)]
        d = R.by_reserve(s)
        assert d["m"] == sum(c["m"] for c in cells) == 200
        assert d["n_front_inst"] == sum(c["n_front_inst"] for c in cells)
        assert sum(d["per_k"][str(k)]["n_front_inst"] for k in (3, 5)) == d["n_front_inst"]
        assert d["excess0"] == pytest.approx(sum(c["excess0"] * c["m"] for c in cells) / d["m"])


def test_faktoren_anteile_stimmen_mit_den_zellen_ueberein():
    for fac, levels in DATA["factors"].items():
        assert sum(v["cells"] for v in levels.values()) == 32
        for lvl, v in levels.items():
            sub = [c for c in R.cells() if str(c[fac]) == lvl]
            assert v["cells"] == len(sub) and v["front"] == sum(c["klass"] == "front" for c in sub)


def test_formel_zellen_und_anpassung_haben_die_erwartete_form():
    f = DATA["formel"]
    assert f["n_fit"] == 192 and len(f["cells"]) == 16 and f["a"] > 0 and f["b"] > 0
    assert f["n_hold"] == sum(c["err_mean"] <= C.ERR_HOLD for c in f["cells"]) and f["n_break"] == sum(c["err_mean"] >= 10.0 for c in f["cells"])
    assert f["err_min"] == pytest.approx(min(c["err_mean"] for c in f["cells"])) and f["err_max"] == pytest.approx(max(c["err_mean"] for c in f["cells"]))
    assert {c["k"] for c in f["cells"]} == {2, 3, 5, 8} and all(c["m"] == 25 for c in f["cells"])


def test_groessenwahl_tabelle_zaehlungen_sind_in_sich_stimmig():
    for q in DATA["qstern"]:
        assert q["cases"] == 100 and sum(q["true_cnt"].values()) == 100 == sum(q["pred_cnt"].values())
        assert q["hit_inner"] <= q["hit_all"] <= q["cases"] and q["hit_inner"] <= q["inner"] and q["hit_all"] <= q["near"] <= q["cases"]
        assert q["inner"] == q["true_cnt"]["3"] + q["true_cnt"]["5"]


def test_ortools_orakel_und_mengen_abschnitte_haben_ihre_zaehlungen():
    ort = DATA["ort"]
    assert ort["runs"] == 1600 and ort["n_infeasible"] == 0 and ort["n_error"] == 0 and ort["best_of_two"]["runs"] == 800
    orc = DATA["orakel"]
    assert orc["all"]["cases"] == 336 == sum(orc[s]["cases"] for s in ("0.0", "0.02", "0.1"))
    assert all(orc[s]["n_below"] == 0 for s in ("0.0", "0.02", "0.1"))                       # nie unter dem exakten Optimum
    mg = DATA["mengen"]
    assert set(mg) == {"gleich", "weit", "schief", "fast"}
    for dist in mg.values():
        assert all(dist[str(s)]["cells"] == 8 and dist[str(s)]["m"] == 64 for s in C.RESERVE_OPTIONS)


def test_neue_felder_kipppunkt_paar_bias_orakel_und_ort_sind_in_sich_stimmig():
    for c in DATA["cells"]:
        if c["n_front_inst"]:
            qs = c["fpair_quartiles"]
            assert c["fpair_median"] >= 0 and (qs is None or qs[0] <= qs[1] <= qs[2])
            assert c["n_same_dist"] <= c["n_front_inst"]
        else:
            assert c["fpair_median"] is None and c["n_same_dist"] == 0
        assert c["vmin"] <= c["Vend"] and c["n_v400_at_bound"] <= c["m"]
    assert DATA["meta"]["n_v400_at_bound"] == sum(c["n_v400_at_bound"] for c in DATA["cells"])
    f = DATA["formel"]
    assert f["inst_n"] == 400 and f["inst_err_mean"] <= f["inst_err_max"] and f["bias_min"] <= f["bias_max"] and 0 <= f["inst_over10"] <= f["inst_n"]
    bo = DATA["ort"]["best_of_two"]
    assert bo["equal"] + bo["better"] <= bo["runs"] and bo["over5"] <= bo["over1"] <= bo["runs"] and DATA["ort"]["best_of_two_k35"]["runs"] == 640
    assert set(DATA["ort"]["secs_ort"]) == {"20", "40"} and all(v > 0 for v in DATA["ort"]["own_secs_per_stage"].values())
    z = DATA["orakel"]["0.0"]
    assert z["instances"] == 16 and 0 <= z["instances_over_half"] <= z["n_over_half"] and z["live_cases"] == 48
    for x in DATA["qstern"]:
        assert x["const_hit"] == max(x["true_cnt"].values())
