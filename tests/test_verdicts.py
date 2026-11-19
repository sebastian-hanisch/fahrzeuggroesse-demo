"""Verdikte als reine Funktionen (DEMO-PLAYBOOK §12): Schwellen und jede Zahl im Text an handgesetzten Werten."""

import pytest

import fgr_constants as C
import fgr_evaluation as E


def make_cell(dv, n_front=14, m=25, fix_less=12, price=4.2, fpair=28.85, excess=0.75):
    return {"ci": 7, "n": 40, "depot": "mitte", "k": 5, "s": 0.0, "m": m, "dV": dv, "n_front_inst": n_front, "n_less_at_f": {str(f): fix_less for f in C.FIX_OPTIONS[1:]},
            "price_front_inst": price, "fpair_median": fpair, "excess0": excess}


def sol(key, v, d, f=0):
    return E.Sol(key, key, f, (), d, v)


@pytest.mark.parametrize("dv,want", [(0.3, "front"), (0.2999, "zwischen"), (0.1, "zwischen"), (0.0999, "keine"), (0.0, "keine"), (1.5, "front")])
def test_klassengrenzen_sind_an_der_schwelle_inklusive_nach_oben(dv, want):
    assert E.klass_of(dv) == want


def test_meldung_zielkonflikt_nennt_zahlen_der_zelle_und_ist_eine_warnung():
    kind, text = E.verdict_level(make_cell(0.56), 50)
    assert kind == "warning" and text.startswith("**Zielkonflikt.**")
    for part in ("Zelle 7", "40 Kunden", "5 Ladungen", "0 % Reserve", "ΔV = 0,56", "in 14 von 25 Instanzen", "Bei dem gewählten f = 50", "in 12 von 25 Instanzen",
                 "im Mittel 4,2 % mehr Distanz als die kürzeste", "rechnerischer Kipppunkt f* = (D₄₀₀ − D₀) / (V₀ − V₄₀₀) im Median 28,9"):
        assert part in text, part


def test_meldung_grenzfall_ist_eine_information_ohne_preis():
    kind, text = E.verdict_level(make_cell(0.2, n_front=6), 50)
    assert kind == "info" and "Grenzfall" in text and "mehr Distanz" not in text and "in 6 von 25 Instanzen sinkt" in text


def test_meldung_kein_zielkonflikt_ist_ein_erfolg_und_nennt_den_ueberschuss():
    kind, text = E.verdict_level(make_cell(0.04, n_front=1, fix_less=0, excess=0.05), 100)
    assert kind == "success" and "**Kein Zielkonflikt**" in text and "in 1 von 25 Instanzen sinkt" in text and "0,05 Fahrzeuge mehr als die untere Schranke" in text
    assert "in 0 von 25 Instanzen" in text


def test_meldung_bei_f_gleich_null_sagt_dass_es_nichts_zu_tauschen_gibt():
    _kind, text = E.verdict_level(make_cell(0.56), 0)
    assert "Bei f = 0 gibt es nichts zu tauschen" in text and "gewählten f" not in text


def test_meldung_instanz_kipppunkt_und_richtung_je_nach_gewaehltem_f():
    f0, f400 = sol("f0", 6, 10000), sol("f400", 5, 10500)        # Kipppunkt (10500 − 10000) / 10 Einheiten = 50 Längeneinheiten
    a = E.Analysis(None, (f0, sol("sel", 6, 10000, 25), f400), 1.0)
    kind, text = E.verdict_instance(E.Settings(fix=25), a)
    assert kind == "info" and "f* = 50,0" in text and "6 Fahrzeuge bei 1000,0" in text and "5 bei 1050,0" in text and "die mit mehr Fahrzeugen" in text
    _kind, text = E.verdict_instance(E.Settings(fix=100), a)
    assert "die mit weniger Fahrzeugen" in text


def test_meldung_instanz_ohne_weniger_fahrzeuge_sagt_nur_gefunden_nicht_bewiesen():
    a = E.Analysis(None, (sol("f0", 6, 10000), sol("sel", 6, 10000, 50), sol("f400", 6, 10000)), 1.0)
    _kind, text = E.verdict_instance(E.Settings(), a)
    assert "keine Lösung mit weniger Fahrzeugen" in text and "kein Beweis" in text


def test_meldung_instanz_dominierende_loesung_ist_kein_zielkonflikt():
    a = E.Analysis(None, (sol("f0", 6, 10000), sol("sel", 5, 9900, 50), sol("f400", 5, 9900)), 1.0)
    _kind, text = E.verdict_instance(E.Settings(), a)
    assert "nicht länger" in text and "kein Zielkonflikt" in text


def test_meldung_ortools_kippt_bei_besserer_loesung_auf_erfolg():
    kind, text = E.verdict_ortools(1000.0, {"Standard": 1010.0, "SAVINGS": 995.0}, 3)
    assert kind == "success" and "Standard: 1010,0 (+1,00 % gegen die eigene Suche)" in text and "SAVINGS: 995,0 (−0,50 % gegen die eigene Suche)".replace("−", "-") in text.replace("−", "-")
    kind, text = E.verdict_ortools(1000.0, {"Standard": 1010.0, "SAVINGS": 1020.0}, 3)
    assert kind == "info" and "3 s je Einstellung" in text and "Eigene Suche: 1000,0" in text


def test_hilfsfunktionen_texte():
    assert E.minus_percent(1.94) == "−1,9 %" and E.minus_percent(0) == "±0,0 %"
    assert E.reserve_text(0.02) == "2 %" and "Gebietsrand" in E.depot_text("rand") and "Mitte" in E.depot_text("mitte")
    assert E.km(12345) == "1234,5"
    assert E.cost(sol("a", 6, 10000), 50) == 6 * 50 + 1000


def test_auslastung_von_hand():
    class Inst:
        dem = [0, 10, 10, 10]
        Q = 20
    assert E.utilisation(Inst, sol("a", 2, 0)) == pytest.approx(100.0 * 30 / 40)


def test_hebel_meldung_nennt_die_reserve_als_staerksten_faktor_und_bindet_trennt_an_den_massstab():
    kind, text = E.verdict_hebel()
    assert kind == "info"
    assert "stärkste der vier Faktoren" in text and "verschieben den Anteil ebenfalls" in text and "gesetzten Maßstab" in text and "erfüllt nur der Faktor Reserve" in text
    assert "vier, die anderen Faktoren haben zwei Stufen" in text and "nach einer Erkundung gesetzt" in text
    assert "trennt nur" not in text


def test_formel_meldung_nennt_zellen_und_instanzfehler_und_den_testbereich():
    import fgr_results as R
    f = R.load()["formel"]
    _kind, text = E.verdict_formel()
    assert f"{f['n_hold']} von {len(f['cells'])} Zellen" in text and "in denselben 16 Zellen" in text and "gegen die Lösung der eigenen Suche" in text
    assert f"{f['inst_over10']} von {f['inst_n']} Instanzen erreichen 10 % oder mehr" in text and R.num(f["inst_err_max"]) in text


def test_loesungsbeschriftungen_nennen_keine_garantierte_mindestzahl():
    a = E.analyse(E.Settings(n=20, ils=5, seed=3))
    labels = [s.label for s in a.sols]
    assert labels == ["Kürzeste Lösung (f = 0)", f"Kostenoptimal bei f = {C.DEFAULT_FIX}", "Lösung bei f = 400"]
    assert not any("Wenigste" in label or "Mindest" in label for label in labels)
