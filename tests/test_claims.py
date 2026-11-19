"""Aussagen gegen Zählungen (DEMO-PLAYBOOK §11a): JEDE Zahl der README wird hier aus `data/fgr_results.json` nachgerechnet und steht zugleich als Text in der README.

Aufbau je Test: (1) die Zahl aus den Zellen der Ergebnisdatei rechnen (Zählung über das ganze Raster, nicht eine Zelle), (2) denselben Wortlaut in der README suchen. Wer die README ändert,
ohne die Messung zu ändern, bricht (2); wer die Messung ändert, bricht (1). Die Rohdaten selbst liegen nicht im Repo (`tools/messreihe.py`, `tools/dump_results.py`); ihre Verdichtung ist an
Handwerten geprüft (`tests/test_results.py`). Die Spalte „Test“ der Befunde-Tabelle der README nennt den Test, der die Zeile belegt. „Messung dieser README, nicht im Test“ steht dort, wo
eine Zahl nur aus der Rohmessung kommt."""

import re
import subprocess
import sys
from pathlib import Path

import pytest

import fgr_constants as C
import fgr_results as R

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
D = R.load()
n = R.num
RES = C.RESERVE_OPTIONS


def has(*texts):
    for t in texts:
        assert t in README, t


def slash(values, digits=0):
    return " / ".join(n(v, digits) for v in values)


def test_jeder_testname_der_befundetabelle_existiert():
    names = set(re.findall(r"`(test_claim_[a-z0-9_]+)`", README))
    assert len(names) >= 12
    defined = set(re.findall(r"^def (test_claim_[a-z0-9_]+)\(", Path(__file__).read_text(encoding="utf-8"), re.M))
    assert names <= defined, names - defined


def test_claim_a_zielkonflikt_zellen_je_reserve():
    k = R.klass_counts()
    per = [R.reserve_counts(s)["front"] for s in RES]
    assert k["front"] + k["keine"] + k["zwischen"] == 32 and sum(per) == k["front"]
    has(f"Von den 32 Zellen mit 3 oder 5 Ladungen sind {k['front']} Zielkonflikt, {k['keine']} kein Zielkonflikt und {k['zwischen']} Grenzfälle",
        f"bei 0 % Reserve {per[0]} von 8 Zellen, bei 2 % {per[1]} von 8, bei 5 % {per[2]} von 8 und bei 10 % {per[3]} von 8")


def test_claim_b_reserve_ist_der_staerkste_faktor():
    f = D["factors"]
    share = lambda fac, lv: R.pct(f[fac][lv]["share"])           # noqa: E731
    dv = lambda fac, lv: n(f[fac][lv]["dV_mean"], 2)             # noqa: E731
    assert R.separating_factors() == ["s"]
    # Ladungen und Kunden verdoppeln bzw. halbieren den Anteil (Wortlaut der README)
    assert f["k"]["5"]["share"] == pytest.approx(2 * f["k"]["3"]["share"]) and f["n"]["40"]["share"] == pytest.approx(f["n"]["20"]["share"] / 2)
    assert len(f["s"]) == 4 and all(len(f[x]) == 2 for x in ("k", "n", "depot"))
    has(f"nach Reserve {share('s', '0.0')} / {share('s', '0.02')} / {share('s', '0.05')} / {share('s', '0.1')} % (mittleres ΔV {dv('s', '0.0')} / {dv('s', '0.02')} / {dv('s', '0.05')} / {dv('s', '0.1')})",
        f"nach Ladungen {share('k', '3')} % (3) und {share('k', '5')} % (5) (ΔV {dv('k', '3')} und {dv('k', '5')})", f"nach Kunden {share('n', '20')} % (20) und {share('n', '40')} % (40) (ΔV {dv('n', '20')} und {dv('n', '40')})",
        f"nach Depot {share('depot', 'rand')} % (Rand) und {share('depot', 'mitte')} % (Mitte)", "Die Reserve ist der stärkste der vier Faktoren",
        "erfüllt nur sie, Ladungen und Kundenzahl verdoppeln bzw. halbieren den Anteil", "Die Reserve hat vier, die anderen Faktoren haben zwei Stufen")


def test_claim_c_instanzen_mit_weniger_fahrzeugen():
    parts = []
    for s in RES:
        d = R.by_reserve(s)
        assert d["m"] == 200
        parts.append(f"{R.pct(d['per_k']['3']['n_front_inst'] / 100)} / {R.pct(d['per_k']['5']['n_front_inst'] / 100)} %")
    luft = R.by_reserve(0.05)["n_front_inst"] + R.by_reserve(0.1)["n_front_inst"]
    assert R.by_reserve(0.05)["m"] + R.by_reserve(0.1)["m"] == 400 and luft < 0.05 * 400
    has(f"ab 5 % Reserve sinkt die Fahrzeugzahl bis f = 400 in nur {luft} von 400 Instanzen")
    has("Instanzen mit weniger Fahrzeugen bei f = 400 als bei f = 0 (je 100 Instanzen, 3 / 5 Ladungen): bei 0 % Reserve " + parts[0] + ", bei 2 % " + parts[1]
        + ", bei 5 % " + parts[2] + ", bei 10 % " + parts[3])


def test_claim_d_kipppunkt_und_preis():
    d0, d2 = R.by_reserve(0.0), R.by_reserve(0.02)
    prices = [R.by_reserve(s)["price_mean"] for s in RES]
    cnt = [R.by_reserve(s)["n_front_inst"] for s in RES]
    assert d0["fpair_quartiles"] is not None and all(p is not None for p in prices)
    stufen0 = [sum(d0["per_k"][k]["fstar_counts"][str(f)] for k in ("3", "5")) for f in C.FIX_OPTIONS[1:]]
    assert sum(stufen0) == d0["n_front_inst"] == d0["n_fstar"]                                 # jede Instanz mit weniger Fahrzeugen hat genau eine erste Stufe
    has(f"Rechnerischer Kipppunkt f* = (D₄₀₀ − D₀) / (V₀ − V₄₀₀) (Instanzen mit weniger Fahrzeugen) bei 0 % Reserve {R.fpair_text(d0)} ({d0['n_front_inst']} Instanzen)",
        f"bei 2 % {R.fpair_text(d2)} ({d2['n_front_inst']} Instanzen)",
        "erste Fixkostenstufe mit weniger Fahrzeugen bei 0 % Reserve in " + " / ".join(str(x) for x in stufen0) + " Instanzen (Stufen 10 / 25 / 50 / 100 / 200 / 400)",
        "Lösung bei f = 400 gegen die bei f = 0 in den Instanzen mit weniger Fahrzeugen im Mittel " + ", ".join(f"{n(p)} % ({c} Instanzen)" for p, c in zip(prices, cnt)))


def test_claim_e_ueberschuss_ueber_der_unteren_schranke():
    ex = [R.by_reserve(s)["excess0"] for s in RES]
    assert ex == sorted(ex, reverse=True)
    has("nutzt im Mittel " + " / ".join(n(x, 2) for x in ex) + " Fahrzeuge mehr als die untere Schranke")


def test_claim_f_front_ist_eine_stufe():
    mx = max(c["max_distinct_V"] for c in R.cells(False))
    assert mx == 2 and D["meta"]["rows_m1"] == 1000
    has("In keiner der 1 000 Instanzzeilen kommen mehr als zwei verschiedene Fahrzeugzahlen vor")


def test_claim_g_groesste_und_kleinste_zelle():
    cs = R.cells()
    big = max(cs, key=lambda c: c["dV"])
    assert big["dV"] > 0.5
    has(f"größtes ΔV: Zelle {big['ci']} ({big['n']} Kunden, Depot {'Rand' if big['depot'] == 'rand' else 'Mitte'}, {big['k']} Ladungen, {n(100 * big['s'], 0)} % Reserve) mit {n(big['dV'], 2)}")


def test_claim_h_formel():
    f = D["formel"]
    assert f["n_fit"] == 192 and f["n_break"] == 0 and f["inst_n"] == 400
    has(f"a = {n(f['a'], 3)}, b = {n(f['b'], 3)}", f"mittlerer Fehler auf den Anpassungsdaten {n(f['err_fit_mean'])} % (größter {n(f['err_fit_max'])} %)",
        f"{f['n_hold']} von 16 Zellen höchstens 5 %", f"Spanne {n(f['err_min'])} bis {n(f['err_max'])} %", f"Mittel über die Zellen {n(f['err_mean_all'])} %", "keine Zelle erreicht 10 %",
        f"je Instanz im Mittel {n(f['inst_err_mean'])} % (größter {n(f['inst_err_max'])} %), {f['inst_over10']} von {f['inst_n']} Instanzen ab 10 %",
        "in denselben 16 Zellen wie angepasst (andere Zufalls-Seeds), gegen die Lösung der eigenen Suche, nicht gegen das Optimum",
        f"Zell-Bias zwischen {n(f['bias_min'])} und {n(f['bias_max'], 1, True)} %")


def test_claim_i_groessenwahl():
    q = D["qstern"]
    big = [x for x in q if x["sigma"] >= 1.0]
    assert len(big) == 12 and all(x["true_cnt"]["8"] == 100 and x["pred_cnt"]["8"] == 100 and x["inner"] == 0 for x in big)
    small = {(x["sigma"], x["f"]): x for x in q if x["sigma"] < 1.0}
    assert all(small[(s, 200)]["inner"] == 0 for s in (0.4, 0.5)) and all(small[(s, f)]["inner"] > 0 for s in (0.4, 0.5) for f in (25, 50, 100))
    a25, a100, b25 = small[(0.5, 25)], small[(0.5, 100)], small[(0.4, 25)]
    assert a100["hit_inner"] < 0.1 * a100["inner"]                                             # bei f = 100 trifft die Formel die innere Stufe selten
    assert a100["pred_cnt"]["2"] >= 95 and a100["const_hit"] == a100["true_cnt"]["2"]           # die Formel wählt bei f = 100 fast immer k = 2, und k = 2 ist dort die häufigste beste Größe
    has("Kostenfamilie: Fixkosten und Kilometerkosten je Fahrzeug wachsen mit q^σ (q = Q / Q_ref, Q_ref = Q bei k = 2), σ < 1 ist Größenvorteil, σ > 1 Größennachteil; vier Größen k = 2, 3, 5, 8 bei 10 % Reserve; „innere Stufe“ heißt k = 3 oder 5",
        "Für σ = 1, 1,5 und 2 ist das kleinste Fahrzeug (k = 8) bei allen vier Fixkostenstufen (25, 50, 100, 200) in allen 100 Fällen je Zeile das billigste, bei Messung und Formel",
        f"σ = 0,5, f = 25: {a25['inner']} von 100 Fällen mit innerer Stufe als bester, Formel trifft dieselbe Stufe in {a25['hit_all']} von 100 ({a25['hit_inner']} von {a25['inner']} bei innerer Stufe), die beste konstante Wahl in {a25['const_hit']} von 100",
        f"σ = 0,5, f = 100: {a100['inner']} von 100, Formel trifft {a100['hit_all']} von 100 ({a100['hit_inner']} von {a100['inner']} bei innerer Stufe), die beste konstante Wahl (k = 2) {a100['const_hit']} von 100",
        f"σ = 0,4, f = 25: {b25['inner']} von 100, {b25['hit_all']} von 100 ({b25['hit_inner']} von {b25['inner']}), konstant {b25['const_hit']} von 100",
        "bei f = 200 ist für σ = 0,4 und 0,5 in keinem Fall eine innere Stufe die beste", "kleinere σ als 0,4 sind nicht gemessen")


def test_claim_j_ortools():
    o = D["ort"]
    bo = o["best_of_two"]
    assert o["runs"] == 1600 and bo["runs"] == 800 and o["n_infeasible"] == 0 and bo["median"] == 0.0
    so, os_ = o["secs_ort"], o["own_secs_per_stage"]
    has(f"{o['runs']} Läufe", f"Je Lauf die bessere der beiden Einstellungen im Mittel {n(bo['mean'], 2, True)} % gegen die eigene Suche (OR-Tools besser in {bo['better']} von {bo['runs']} Läufen, größte Abweichung {n(bo['max'], 1, True)} %)",
        f"in {bo['equal']} von {bo['runs']} Läufen gleich (Median {n(bo['median'], 1)} %, {bo['over1']} Läufe über 1 %, {bo['over5']} über 5 %)",
        f"OR-Tools bekam je Fixkostenstufe {n(float(so['20']), 0)} s (20 Kunden) bzw. {n(float(so['40']), 0)} s (40 Kunden) je Einstellung, die Zahl „bessere der beiden Einstellungen“ also das Doppelte",
        f"die eigene Kette brauchte im Mittel {n(os_['20'], 1)} s bzw. {n(os_['40'], 1)} s je Fixkostenstufe", "Gleiche Rechenzeit wurde nicht gemessen", "keine Obergrenze und keine Rangfolge der Löser",
        "höchstens ⌈Σd / Q⌉ + 4 Fahrzeuge")


def test_claim_k_orakel_bei_12_kunden():
    o = D["orakel"]
    z = o["0.0"]
    assert z["cases"] == 112 and z["instances"] == 16 and all(o[s]["n_below"] == 0 for s in ("0.0", "0.02", "0.1")) and z["instances_over_half"] == 1
    has("12 Kunden, k = 3, Reserve 0, 2 und 10 % (5 % nicht gerechnet), 16 Instanzen × 7 Fixkostenstufen = 112 Fälle je Reserve, nicht unabhängig",
        f"mittlere Kostenlücke bei Reserve 0 % {n(z['gap_mean'], 3)} % ({z['n_over_half']} von {z['cases']} Fällen über 0,5 %, größte {n(z['gap_max'], 2)} %, die Fälle über 0,5 % aus {z['instances_over_half']} Instanz)",
        f"bei 2 % {n(o['0.02']['gap_mean'], 3)} %, bei 10 % {n(o['0.1']['gap_mean'], 3)} %",
        f"ein Durchgang über die sieben Stufen {n(z['pass1_gap_mean'], 3)} % ({z['pass1_n_over_half']} Fälle über 0,5 % aus {z['pass1_instances_over_half']} Instanzen)",
        f"Live-Kette der App (f = 0, 100, 400) über {z['live_cases']} Fälle {n(z['live_gap_mean'], 3)} %, die Kette der Messreihe auf denselben {z['live_cases']} Fällen {n(z['chain48_gap_mean'], 3)} %",
        "Das Orakel misst die Kostenlücke, nicht die Höhe des Zielkonflikts")


def test_claim_l_andere_mengenverteilungen():
    mg = D["mengen"]
    for dist in ("gleich", "weit", "schief", "fast"):
        assert all(mg[dist][str(s)]["cells"] == 8 and mg[dist][str(s)]["m"] == 64 for s in RES)
    rows = {d: [mg[d][str(s)]["front_cells"] for s in RES] for d in ("gleich", "weit", "schief", "fast")}
    has(*(f"{label}: " + " / ".join(str(v) for v in rows[d]) for d, label in (("gleich", "gleich 5 bis 25"), ("weit", "weit 1 bis 40"), ("schief", "schief"), ("fast", "fast gleich 14 bis 16"))))
    assert max(rows[d][2] for d in ("weit", "schief", "fast")) <= 1 and max(rows[d][3] for d in ("weit", "schief", "fast")) == 0
    assert rows["weit"][2] == 1 and rows["fast"][1] == 3 > rows["gleich"][1] == 2 and mg["weit"]["0.05"]["front_cell_inst"] == [3]
    qb = [mg["schief"][str(s)]["qmax_bindet"] for s in RES]
    has("bei „weit 1 bis 40“ bleibt bei 5 % Reserve eine Zelle (von 8) mit Zielkonflikt (3 von 8 Instanzen mit weniger Fahrzeugen)",
        "bei „fast gleich 14 bis 16“ liegen die Zielkonflikt-Zellen bei 2 % Reserve (3 von 8) über der Kontrolle „gleich 5 bis 25“ (2 von 8)",
        "bei „schief“ bindet die größte Menge die Kapazität in " + " / ".join(str(x) for x in qb) + " von 64 Instanzen (Reserve 0 / 2 / 5 / 10 %)")


def test_claim_m_abweichungen_zur_vormessung():
    v = D["vormessung"]
    h = v["haupt"]
    k = R.klass_counts()
    now_front = [R.reserve_counts(s)["front"] for s in RES]
    now_n = [R.by_reserve(s)["n_front_inst"] for s in RES]
    big = max(R.cells(), key=lambda c: c["dV"])
    has(f"Zielkonflikt / kein Zielkonflikt / Grenzfall {k['front']} / {k['keine']} / {k['zwischen']} (Vormessung {h['n_front']} / {h['n_keine']} / {h['n_zwischen']})",
        f"Zielkonflikt-Zellen je Reserve {slash(now_front)} (Vormessung {slash(h['front_je_reserve'])})",
        f"Instanzen mit weniger Fahrzeugen je Reserve {slash(now_n)} (Vormessung {slash(h['n_front_inst_je_reserve'])})",
        f"a = {n(D['formel']['a'], 3)} und b = {n(D['formel']['b'], 3)} (Vormessung {n(v['formel']['a'], 3)} und {n(v['formel']['b'], 3)})",
        f"größtes ΔV {n(big['dV'], 2)} (Vormessung {n(h['max_dV'], 2)})", "Auswahl, nicht vollständig", "Packungsstart ist die naheliegende, aber nicht isolierte Ursache",
        f"OR-Tools wurde neu gerechnet (zeitbegrenzt, nicht deterministisch): schon die neuen OR-Tools-Läufe gegen die alte eigene Suche liegen bei {n(v['ort']['neue_ort_gegen_alte_suche_mean'], 2, True)} % (besser in {v['ort']['neue_ort_gegen_alte_suche_better']} von {v['ort']['runs']})",
        f"der Wechsel der Zahl kommt also größtenteils vom Neulauf, und {v['ort']['better']} gegen {D['ort']['best_of_two']['better']} von {v['ort']['runs']} liegt im Rauschen")
    assert big["dV"] > h["max_dV"]


def test_claim_s_untere_schranke_gleiche_distanz_und_dv_gleich_anteil():
    meta, cs = D["meta"], R.cells(False)
    at_bound = meta["n_v400_at_bound"]
    miss = [c for c in cs if c["n_v400_at_bound"] < c["m"]]
    assert at_bound == sum(c["n_v400_at_bound"] for c in cs) == 990 and all(c["s"] == 0.0 for c in miss)
    same = sum(c["n_same_dist"] for c in cs)
    assert same == 3
    assert all(c["dV"] == pytest.approx(c["n_front_inst"] / c["m"]) for c in cs)                  # ΔV ist exakt der Anteil der Instanzen mit weniger Fahrzeugen (V sinkt höchstens um eins)
    has(f"in {at_bound} von {meta['rows_m1']} Instanzen die untere Schranke ⌈Σd / Q⌉ an Fahrzeugen", "alle bei 0 % Reserve", "ob die Schranke dort unerreichbar ist oder die Suche sie verfehlt, ist nicht unterschieden",
        f"In {same} Instanzen mit weniger Fahrzeugen ist die Distanz bei f = 400 nicht länger", "ΔV ist zugleich der Anteil der Instanzen, in denen die Fahrzeugzahl sinkt")


def test_claim_t_flottenmix_der_vormessung():
    mx = D["vormessung"]["mix_n12"]
    has(f"bei 12 Kunden (Vormessung, nicht neu gerechnet; nur σ = {n(mx['sigma'], 0)}, Kapazitätspaar k = 8 und 3, f = {mx['f']}, {mx['instanzen']} Instanzen) liegt der exakte Mix im Mittel {n(mx['gegen_beste_einheitsflotte'], 2)} % unter der besten der vier Einheitsflotten",
        f"{n(mx['gegen_bessere_des_paares'], 2)} % unter der besseren der beiden des Paares")


def test_claim_n_vormessung_orakel_unveraendert_zitiert():
    o = D["vormessung"]["orakel_n12"]
    has(f"mittlere Lücke {n(o['reserve_0']['mittel'], 3)} % ({o['reserve_0']['ueber_halb']} von {o['reserve_0']['faelle']} Fällen über 0,5 %, größte {n(o['reserve_0']['max'], 2)} %)")


def test_claim_p_raster_seeds_und_einstellungen_der_readme():
    meta = D["meta"]
    assert len(D["cells"]) == 40 and len(R.cells()) == 32 and len(D["formel"]["cells"]) == 16 and D["formel"]["n_fit"] == 192
    assert all(c["m"] == 25 for c in D["cells"]) and meta["rows_m1"] == 1000 and meta["fs"] == list(C.FIX_OPTIONS) and meta["iters"] == C.MEASURE_ILS == 400
    s = meta["seeds_m1"], meta["seeds_fit"], meta["orakel_seeds"], meta["mengen_seeds"]
    has("40 Zellen, je 25 Instanzen", "Zufalls-Seeds 300000 bis 300024", f"({s[1][0]} bis {s[1][1]})", "1 000 Instanzzeilen in 40 Zellen", "192 Lösungen",
        f"{C.ORTOOLS_SECONDS[20]} s (20 Kunden) bzw. {C.ORTOOLS_SECONDS[40]} s (40 Kunden)", "100 oder 400 Iterationen", "400 Iterationen")
    assert s[0] == [300000, 300024] and s[2] == [2000, 2007] and s[3] == [310000, 310007]
    has("2000 bis 2007", "310000 bis 310007")


def test_claim_q_vormessung_plattform_und_erkundung():
    v = D["vormessung"]
    has(f"{v['plattform']['identisch']} von {v['plattform']['zeilen']} Zeilen gleich",
        f"({v['erkundung']['seeds'][0]} bis {v['erkundung']['seeds'][1]}, n = 20 und 40, Depot Rand, {v['erkundung']['iterationen']} Iterationen)")


def test_claim_r_nicht_neu_gerechnete_vormessungszahlen_stehen_als_solche_in_der_readme():
    v = D["vormessung"]
    a, k = v["abstimmung_400_gegen_1500"], v["kontrolle_1500"]
    has(f"mittlere Mehrkosten {n(a['mehrkosten_mittel'], 2)} %, größte {n(a['mehrkosten_max'], 2)} %, {a['laeufe']} Läufe",
        f"Fahrzeugzahl in {k['fahrzeugzahl_verschieden']} von {k['werte']} Werten verschieden, Zielkonflikt-Zellen {k['front_zellen_400']} gegen {k['front_zellen_1500']}", "Nicht neu gerechnet")


def test_claim_o_testzahl_der_readme_stimmt_mit_der_suite_ueberein():
    out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", str(ROOT / "tests")], capture_output=True, text=True, cwd=ROOT, check=False).stdout
    total = int(re.search(r"(\d+) tests? collected", out).group(1))
    has(f"{total} Tests")


def test_keine_umgebungsaussagen_und_keine_toten_dateilinks_in_der_readme():
    assert not re.search(r"\]\((?!https?://|#)[A-Za-z0-9_./-]+\.(py|json|txt)\)", README)
    for wort in ("läuft lokal", "Saatwert", " trägt ", " tragen ", "TODO"):
        assert wort not in README, wort


@pytest.mark.parametrize("pflicht", ["## Warum dieses Problem", "## Modell", "## Methodik", "## Befunde (gemessen, keine Behauptungen)", "## Ehrliche Grenzen", "## Verifikation", "## Dateistruktur", "## Bewusst nicht umgesetzt"])
def test_readme_hat_die_pflichtabschnitte(pflicht):
    assert pflicht in README
