"""Presets: Vollständigkeit, gültige Werte, Standard-Preset = Standardeinstellungen, Zelle und Geschichte jedes Presets (Abnahme gegen die Ergebnisdatei und den Lauf)."""

import pytest

import fgr_constants as C
import fgr_evaluation as E
import fgr_presets as P
import fgr_results as R
import fgr_stories as ST


def cell_of(name):
    p = C.PRESETS[name]
    return R.cell_of(p["n"], p["depot"], p["k"], p["reserve"])


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP) == set(ST.STORIES)
    for name, preset in C.PRESETS.items():
        assert set(preset) == set(P.PRESET_KEYS), name
        assert C.PRESET_HELP[name]


def test_preset_values_sind_gemessene_stufen_und_der_seed_liegt_ausserhalb_der_messreihen():
    for name, p in C.PRESETS.items():
        assert p["n"] in C.N_OPTIONS and p["depot"] in C.DEPOT_OPTIONS and p["k"] in C.K_OPTIONS and p["reserve"] in C.RESERVE_OPTIONS and p["fix"] in C.FIX_OPTIONS and p["ils"] in C.ILS_OPTIONS, name
        assert 500000 <= p["seed"] <= C.SEED_MAX                                   # nie 1000 bis 1011, 2000 bis 2007, 300000 bis 300024, 310000 bis 310007


def test_default_preset_equals_the_default_settings():
    assert E.Settings(**C.PRESETS["Standard"]) == E.Settings()
    assert next(iter(C.PRESETS)) == "Standard"


def test_setting_specs_cover_every_preset_key():
    assert set(P.PRESET_KEYS.values()) == set(P.SETTING_SPECS)


def test_permalink_rastet_ein_und_verwirft_unbekanntes():
    spec = P.SETTING_SPECS["reserve_slider"]
    assert P.clamp_value(spec, 0.04) == 0.05 and P.clamp_value(spec, 0.5) == 0.10
    assert P.clamp_value(P.SETTING_SPECS["depot_radio"], "oben") is None and P.clamp_value(P.SETTING_SPECS["depot_radio"], "rand") == "rand"
    seed = P.SETTING_SPECS["seed_input"]
    assert P.clamp_value(seed, -5) == 0 and P.clamp_value(seed, 10 ** 9) == C.SEED_MAX


def test_jedes_preset_wird_nur_einmal_gebraucht_kein_doppeltes_szenario():
    keys = [tuple(sorted(p.items())) for p in C.PRESETS.values()]
    assert len(set(keys)) == len(keys)


# ------------------------------------------------------------------------------------------------ Zellen der Presets gegen die Ergebnisdatei

def test_standard_ist_ein_zielkonflikt_mittlerer_hoehe_und_nicht_das_maximum():
    c = cell_of("Standard")
    assert c["klass"] == "front" and c["n_front_inst"] >= 0.4 * c["m"]
    assert c["dV"] < max(x["dV"] for x in R.cells())


def test_knappe_kapazitaet_20_kunden_ist_die_zelle_mit_dem_groessten_dV():
    c = cell_of("Knappe Kapazität, 20 Kunden")
    assert c["dV"] == max(x["dV"] for x in R.cells()) and c["n"] == 20


def test_grenzfall_hat_bei_2_prozent_reserve_hoechstens_die_haelfte_der_instanzen_mit_zielkonflikt():
    c = cell_of("Grenzfall: 2 % Reserve")
    assert c["s"] == pytest.approx(0.02) and c["klass"] == "zwischen" and 0 < c["n_front_inst"] < c["m"] / 2


def test_genug_reserve_ist_kein_zielkonflikt_ohne_eine_einzige_instanz_mit_weniger_fahrzeugen():
    c = cell_of("Genug Reserve")
    assert c["klass"] == "keine" and c["n_front_inst"] == 0 and c["s"] == pytest.approx(0.10)


def test_wenige_ladungen_ist_ein_zielkonflikt_mit_niedrigerem_kipppunkt_als_der_standard():
    c, std = cell_of("Wenige Ladungen"), cell_of("Standard")
    assert c["k"] == 3 and std["k"] == 5 and (c["n"], c["depot"], c["s"]) == (std["n"], std["depot"], std["s"])
    assert c["klass"] == "front" and c["fpair_median"] < std["fpair_median"]


def test_hilfetexte_nennen_nur_zahlen_der_zelle():
    def facts(name):
        c = cell_of(name)
        return c, C.PRESET_HELP[name]
    c, h = facts("Standard")
    assert f"ΔV {R.num(c['dV'], 2)}" in h and f"in {c['n_front_inst']} von {c['m']} Instanzen" in h and "f = 50" in h
    c, h = facts("Knappe Kapazität, 20 Kunden")
    assert f"größten ΔV ({R.num(c['dV'], 2)})" in h and f"in {c['n_front_inst']} von {c['m']} Instanzen" in h and f"im Mittel {R.num(c['price_front_inst'])} % länger" in h and "f = 100" in h
    c, h = facts("Grenzfall: 2 % Reserve")
    assert f"ΔV {R.num(c['dV'], 2)}" in h and f"nur in {c['n_front_inst']} von {c['m']} Instanzen" in h
    c, h = facts("Genug Reserve")
    assert c["n_front_inst"] == 0 and f"in keiner der {c['m']} Instanzen" in h
    c, h = facts("Wenige Ladungen")
    std = cell_of("Standard")
    assert f"ΔV {R.num(c['dV'], 2)}" in h and f"f* = {R.num(c['fpair_median'], 1)}" in h and f"Standard: {R.num(std['fpair_median'], 1)}" in h


# ------------------------------------------------------------------------------------------------ Geschichte auf dem Lauf (Seed des Presets, Rechenbudget des Presets)

@pytest.mark.parametrize("name", list(C.PRESETS))
def test_jedes_preset_zeigt_auf_seinem_lauf_seine_geschichte(name):
    p = C.PRESETS[name]
    st = E.Settings(p["n"], p["depot"], p["k"], p["reserve"], p["fix"], p["ils"], p["seed"])
    a = E.analyse(st)
    assert ST.STORIES[name](a, st), name


def test_geschichte_kriterien_kippen_einzeln_an_ihrer_schwelle():
    def sol(key, v, d, f=0):
        return E.Sol(key, key, f, (), d, v)

    def an(f0, sel, f400):
        return E.Analysis(None, (f0, sel, f400), 0.0)

    st50 = E.Settings(fix=50)
    # Standard: Kipppunkt (10 500 − 10 000) / 10 = 50 liegt gerade noch bei f = 50, die gewählte Lösung hat die Fahrzeuge von f = 400
    f0, f400 = sol("f0", 6, 10000), sol("f400", 5, 10500)
    assert ST.story_standard(an(f0, sol("sel", 5, 10500, 50), f400), st50)
    assert not ST.story_standard(an(f0, sol("sel", 6, 10000, 50), f400), st50)                         # gewählte Lösung hat noch die alten Fahrzeuge
    assert not ST.story_standard(an(f0, sol("sel", 5, 10500, 50), sol("f400", 5, 10501)), st50)        # Kipppunkt 50,1 liegt über f = 50
    assert not ST.story_standard(an(f0, sol("sel", 6, 10000, 50), sol("f400", 6, 10000)), st50)        # kein Zielkonflikt
    # Knapp klein: mindestens 5 % länger
    assert ST.story_knapp_klein(an(f0, f0, sol("f400", 5, 10500)), st50) and not ST.story_knapp_klein(an(f0, f0, sol("f400", 5, 10499)), st50)
    # Grenzfall: weniger Fahrzeuge und Kipppunkt über 2 und höchstens 10 ((10 020 − 10 000) / 10 = 2 zählt nicht, 10 100 ergibt 10)
    assert ST.story_grenzfall(an(f0, f0, sol("f400", 5, 10021)), st50) and not ST.story_grenzfall(an(f0, f0, sol("f400", 5, 10020)), st50)
    assert ST.story_grenzfall(an(f0, f0, sol("f400", 5, 10100)), st50) and not ST.story_grenzfall(an(f0, f0, sol("f400", 5, 10101)), st50)
    # Genug Reserve: gleiche Fahrzeugzahl
    assert ST.story_genug_reserve(an(f0, f0, sol("f400", 6, 11000)), st50) and not ST.story_genug_reserve(an(f0, f0, f400), st50)
    # Wenige Ladungen: Kipppunkt über 5 und höchstens 25 (hier (10250 − 10000) / 10 = 25 und (10050 − 10000) / 10 = 5)
    assert ST.story_wenige_ladungen(an(f0, f0, sol("f400", 5, 10250)), st50) and not ST.story_wenige_ladungen(an(f0, f0, sol("f400", 5, 10251)), st50)
    assert ST.story_wenige_ladungen(an(f0, f0, sol("f400", 5, 10051)), st50) and not ST.story_wenige_ladungen(an(f0, f0, sol("f400", 5, 10050)), st50)
