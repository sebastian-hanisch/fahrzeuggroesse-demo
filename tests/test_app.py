"""End-to-end Smoke-Test via Streamlits offiziellem AppTest-Framework: lädt app.py mit den Standardeinstellungen, klickt jedes Preset, fährt jeden Regler
an seine Stufen und prüft, dass kein Python-Fehler auftritt (insbesondere `StreamlitDuplicateElementId` bei Charts mit gleichem Inhalt).

Die Live-Suche läuft in den Tests mit höchstens 15 Iterationen, OR-Tools mit 1 s Zeitlimit (die Konstanten werden vor dem Lauf umgesetzt); keine Zeit-Assertions."""

import os
import re

import pytest
from streamlit.testing.v1 import AppTest

import fgr_constants as C
import fgr_results as R

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
TIMEOUT = int(os.environ.get("APPTEST_TIMEOUT", "300"))  # unter Last (parallele Läufe) reichen 180 s nicht immer; Umgebungsvariable zum Anpassen


@pytest.fixture(autouse=True)
def kurze_rechnung(schnelle_suche, monkeypatch):
    monkeypatch.setattr(C, "ORTOOLS_SECONDS", {20: 1, 40: 1})


def _fresh_app() -> AppTest:
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    return at


def _texts(at):
    return [w.value for w in list(at.info) + list(at.success) + list(at.warning)]


def _first(at):
    return next(t for t in _texts(at) if re.match(r"\*\*(Zielkonflikt\.|Kein Zielkonflikt|Grenzfall)", t))


def test_app_loads_without_exception_and_shows_the_three_expanders():
    at = _fresh_app()
    labels = [e.label for e in at.expander]
    assert "🔧 Wie wir das erreichen – vollständiger Methodenvergleich" in labels
    assert "Wie funktioniert diese Demo?" in labels and "📐 Mathematische Formulierung" in labels
    assert [m.label for m in at.metric] == [f"Fahrzeuge bei f = {C.DEFAULT_FIX}", "Distanz (Längeneinheiten)", f"Gesamtkosten f · V + D bei f = {C.DEFAULT_FIX}", "Auslastung der Fahrzeuge"]


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_jedes_preset_laeuft_und_zeigt_die_zelle_des_presets(name):
    at = _fresh_app()
    at.sidebar.button(key=f"preset_{name}").click().run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    p = C.PRESETS[name]
    cell = R.cell_of(p["n"], p["depot"], p["k"], p["reserve"])
    first = _first(at)
    assert f"Zelle {cell['ci']}," in first and f"ΔV = {R.num(cell['dV'], 2)}" in first


@pytest.mark.parametrize("key", ["n_radio", "k_radio", "reserve_slider", "fix_slider", "ils_slider", "depot_radio"])
def test_jede_stufe_der_diskreten_regler_laeuft(key):
    at = _fresh_app()
    stufen = {"n_radio": C.N_OPTIONS, "k_radio": C.K_OPTIONS, "reserve_slider": C.RESERVE_OPTIONS, "fix_slider": C.FIX_OPTIONS, "ils_slider": C.ILS_OPTIONS, "depot_radio": C.DEPOT_OPTIONS}[key]
    for value in stufen:
        widget = at.sidebar.radio(key=key) if key.endswith("_radio") else at.sidebar.select_slider(key=key)
        widget.set_value(value).run(timeout=TIMEOUT)
        assert not at.exception, (key, value, [str(e) for e in at.exception])
        assert (at.sidebar.radio(key=key) if key.endswith("_radio") else at.sidebar.select_slider(key=key)).value == value


def test_zufalls_seed_an_den_raendern_und_der_zufalls_knopf():
    at = _fresh_app()
    for value in (0, C.SEED_MAX):
        at.sidebar.number_input(key="seed_input").set_value(value).run(timeout=TIMEOUT)
        assert not at.exception, (value, [str(e) for e in at.exception])
    at.sidebar.button[-1].click().run(timeout=TIMEOUT)   # 🎲 Neue Instanz generieren (letztes Element der Seitenleiste)
    assert not at.exception, [str(e) for e in at.exception]
    assert 0 <= at.sidebar.number_input(key="seed_input").value <= C.SEED_MAX


def test_die_drei_meldungszustaende_kommen_vor():
    """Reserve 0 % mit dem Standard (40 Kunden, Mitte, 5 Ladungen) ist ein Zielkonflikt, 10 % Reserve kein Zielkonflikt, 2 % Reserve (40 Kunden, Mitte) ein Grenzfall."""
    at = _fresh_app()
    assert any(t.startswith("**Zielkonflikt.**") for t in [w.value for w in at.warning])
    at.sidebar.select_slider(key="reserve_slider").set_value(0.10).run(timeout=TIMEOUT)
    assert any("**Kein Zielkonflikt**" in w.value for w in at.success)
    assert not any(w.value.startswith("**Zielkonflikt.**") for w in at.warning)
    at.sidebar.select_slider(key="reserve_slider").set_value(0.02).run(timeout=TIMEOUT)
    assert any("Grenzfall" in w.value for w in at.info)


def test_ortools_und_formel_knoepfe_funktionieren_und_werden_je_einstellung_gespeichert():
    pytest.importorskip("ortools")
    at = _fresh_app()
    at.button(key="ortools_start").click().run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert any("OR-Tools (Gesamtkosten" in i.value for i in list(at.info) + list(at.success))
    at.button(key="formula_start").click().run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert any("Auf dieser Instanz weicht die Formel" in i.value for i in at.info)
    at.sidebar.radio(key="depot_radio").set_value("rand").run(timeout=TIMEOUT)   # andere Einstellung: kein altes Ergebnis mehr
    assert not at.exception
    assert not any("OR-Tools (Gesamtkosten" in i.value for i in list(at.info) + list(at.success))
    assert not any("Auf dieser Instanz weicht die Formel" in i.value for i in at.info)


def test_halteliste_fuer_jede_loesung_stuerzt_nicht_ab():
    at = _fresh_app()
    options = list(at.selectbox(key="view_select").options)
    assert len(options) == 3
    for option in options:
        at.selectbox(key="view_select").set_value(option).run(timeout=TIMEOUT)
        assert not at.exception, (option, [str(e) for e in at.exception])


def test_permalink_rastet_auf_stufen_und_verwirft_unbekanntes():
    at = AppTest.from_file(APP_PATH)
    at.query_params["reserve"] = "0.04"
    at.query_params["depot"] = "oben"
    at.query_params["n"] = "33"
    at.query_params["ils"] = "5"
    at.query_params["fix"] = "70"
    at.run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert at.sidebar.select_slider(key="reserve_slider").value == 0.05 and at.sidebar.radio(key="depot_radio").value == C.DEFAULT_DEPOT
    assert at.sidebar.radio(key="n_radio").value == 40 and at.sidebar.select_slider(key="ils_slider").value == 100
    assert at.sidebar.select_slider(key="fix_slider").value == 50    # 70 liegt näher an 50 als an 100


def test_keine_toten_dateilinks_und_keine_umgebungsaussagen_in_der_app():
    text = open(APP_PATH, encoding="utf-8").read()
    assert not re.search(r"\]\([A-Za-z0-9_./-]+\.(py|json|md|txt)\)", text)
    for wort in ("läuft lokal", "Saatwert", " trägt ", " tragen "):
        assert wort not in text, wort
