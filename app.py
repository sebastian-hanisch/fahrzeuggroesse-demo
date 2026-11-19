"""Fahrzeuge oder Kilometer? Welche Fahrzeuggröße? - interaktive Fall-Demo
Sebastian Hanisch - Operations Research und Machine Learning

CVRP mit Fixkosten je Fahrzeug: Ein Fahrzeug kostet Fixkosten, jeder Kilometer kostet auch. Live auf einer Instanz: die kürzeste Lösung (f = 0), die kostenoptimale Lösung bei dem
gewählten f und die Lösung bei f = 400 mit der eigenen Suche; OR-Tools und die Kontinuumsformel auf Knopfdruck. Die Aussagen stützen sich auf die vorgerechnete Messreihe
(data/fgr_results.json). Aufbau und Regeln: DEMO-PLAYBOOK.md (§2).

Lauffähig mit: streamlit run app.py
"""

import pandas as pd
import streamlit as st

import fgr_constants as C
import fgr_evaluation as E
import fgr_formula as FO
import fgr_model as M
import fgr_results as R
import fgr_search as SR
import fgr_solvers as V
import fgr_visualization as VIZ
from fgr_layout import dunkles_design, kopf_css
from fgr_pdf_export import build_pdf
from fgr_presets import (
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    options,
    randomize_seed,
    sidebar_presets,
    sync_query_params,
)

st.set_page_config(page_title="Fahrzeuggröße – Sebastian Hanisch", layout="wide")


@st.cache_data(show_spinner=False)
def _analysis(settings):
    return E.analyse(settings)


@st.cache_data(show_spinner=False)
def _ortools(settings):
    """OR-Tools in beiden Einstellungen bei dem gewählten f auf derselben Instanz; liefert die Gesamtkosten in Längeneinheiten."""
    inst = E.make_inst(settings)
    secs = C.ORTOOLS_SECONDS[settings.n]
    out = {}
    for setting in V.SETTINGS:
        routes, _obj = V.solve_ortools(inst, settings.fix * M.SCALE, secs, setting)
        if routes is None or M.verify(inst, routes):
            raise RuntimeError(f"OR-Tools ({setting}) lieferte keine zulässige Lösung")
        out[V.SETTING_LABELS[setting]] = M.total_cost(inst, routes, settings.fix * M.SCALE) / M.SCALE
    return out


@st.cache_data(show_spinner=False)
def _formula_points(settings):
    """Die Instanz bei vier Kapazitäten (Reserve 10 %, k = 2, 3, 5, 8), je eine Suche bei f = 0; Punkte (k, Q, D in Entfernungseinheiten)."""
    base = M.make_base(settings.n, M.DEPOTS[settings.depot], settings.seed)
    pts = []
    for k in C.FORMEL_KS:
        inst = M.with_capacity(base, M.capacity(base.dem, k, C.FORMEL_RESERVE))
        routes = SR.solve_fix(inst, 0, settings.ils, settings.seed)
        pts.append((k, inst.Q, M.distance_of(inst, routes)))
    return pts


def _fmt_reserve(value):
    return f"{round(100 * value)} %"


# Fester Kopf: nur der Titel bleibt beim Scrollen oben (Stylesheet in fgr_layout.py).
st.html(kopf_css(dunkles_design()))
with st.container(key="kopf"):
    st.title("🚚 Fahrzeuge oder Kilometer? Welche Fahrzeuggröße?")
st.markdown(
    """
Ein Fahrzeug kostet **Fixkosten**, jeder Kilometer kostet auch. Mehr Fahrzeuge heißen kürzere Wege, weniger Fahrzeuge längere (**CVRP mit Fixkosten je Fahrzeug**). Die Demo fragt: **wann zwingt mich der Preis eines Fahrzeugs
zu längeren Wegen, und wann ist das gar keine Frage?** Du stellst die **Kapazitätsreserve** (wie viel Laderaum über der Mindestmenge) und die **Fixkosten** ein und siehst live auf **einer Instanz** die kürzeste Lösung, die
kostenoptimale und die bei den höchsten gemessenen Fixkosten (f = 400, meist die mit den wenigsten gefundenen Fahrzeugen). Die Aussagen stützen sich auf eine vorgerechnete Messreihe (40 Zellen, je 25 Instanzen, sieben Fixkostenstufen); dazu eine **Formel**, die die Distanz mit zwei Zahlen
vorhersagt.

Weiter unten: die **Kernfragen** und die Expander **🔧 Wie wir das erreichen – vollständiger Methodenvergleich**, **Wie funktioniert diese Demo?** und **📐 Mathematische Formulierung**.
"""
)

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    sidebar_presets()  # Schnellstart oben, das aktive Preset ist hervorgehoben
    st.header("⚙️ Einstellungen")
    st.markdown("**Instanz**")
    n = st.radio("Kunden", options("n_radio"), key="n_radio", horizontal=True, help="Zahl der Kunden (die gemessenen Größen). Bei 40 Kunden dauert die Live-Rechnung länger.")
    depot = st.radio("Depot", options("depot_radio"), key="depot_radio", format_func=lambda v: C.DEPOT_LABELS[v],
                     help="Lage des Depots im 100 × 100-Gebiet. Dieselbe Instanz (gleiche Orte und Mengen) mit beiden Depots ist in der Messreihe gepaart gerechnet.")
    k = st.radio("Ladungen k", options("k_radio"), key="k_radio", horizontal=True,
                 help="Die Mindestzahl Fahrzeuge ist etwa k: Die Kapazität Q ist so bemessen, dass die Gesamtmenge in k Ladungen plus Reserve passt (Q = (1 + Reserve) · Gesamtmenge / k, mindestens die größte Einzelmenge).")
    reserve = st.select_slider("Kapazitätsreserve", options=options("reserve_slider"), key="reserve_slider", format_func=_fmt_reserve,
                               help=f"Wie viel Laderaum über der Mindestmenge liegt. Bei 0 % muss die Gesamtmenge fast exakt in k Fahrzeuge passen; bei 10 % sinkt die Fahrzeugzahl bis f = 400 in {R.by_reserve(0.1)['n_front_inst']} von {R.by_reserve(0.1)['m']} Instanzen der Messreihe (bei 0 %: {R.by_reserve(0.0)['n_front_inst']} von {R.by_reserve(0.0)['m']}).")
    st.markdown("**Kosten**")
    fix = st.select_slider("Fixkosten je Fahrzeug f", options=options("fix_slider"), key="fix_slider",
                           help="Kosten je genutztes Fahrzeug in Längeneinheiten des 100 × 100-Gebiets (ein Kilometer kostet eine Längeneinheit). Die Messreihe rechnet 0, 10, 25, 50, 100, 200 und 400.")
    st.markdown("**Rechnen**")
    ils = st.select_slider("Rechenbudget eigene Suche", options=options("ils_slider"), key="ils_slider", format_func=lambda v: C.ILS_LABELS[v],
                           help="Iterationen der eigenen Suche je Lauf. Die vorgerechnete Messreihe nutzt 400; bei 100 geht die Live-Rechnung schneller, die Lösungen können etwas schlechter sein.")
    seed = st.number_input("Zufalls-Seed der Instanz", *bounds("seed_input"), key="seed_input", step=1)
    st.button("🎲 Neue Instanz generieren", width="stretch", on_click=randomize_seed)

sync_query_params({"n_radio": int(n), "depot_radio": depot, "k_radio": int(k), "reserve_slider": float(reserve), "fix_slider": int(fix), "ils_slider": int(ils), "seed_input": int(seed)})

settings = E.Settings(int(n), depot, int(k), float(reserve), int(fix), int(ils), int(seed))
cell = R.cell_of(settings.n, settings.depot, settings.k, settings.reserve)

# --- Erste Meldung: aus der gemessenen Zelle --------------------------------------------------------------------------------------------------

st.markdown("## 🚚 Gibt es hier einen Zielkonflikt?")
kind, text = E.verdict_level(cell, settings.fix)
getattr(st, kind)(text)

with st.spinner(f"Rechne die drei Lösungen auf einer Instanz mit {settings.n} Kunden (je Lauf {settings.ils} Iterationen) ..."):
    a = _analysis(settings)
f0, sel, f400 = (E.sol_of(a, key) for key in ("f0", "sel", "f400"))

st.markdown("## 🗺️ Eine Instanz")
st.info("Das ist **eine Instanz**. Sie zeigt, wie die drei Lösungen aussehen; die Aussagen darüber, wann es einen Zielkonflikt gibt und wie hoch er ist, stützen sich auf die Messreihe weiter unten (25 Instanzen je Zelle).")
kind, text = E.verdict_instance(settings, a)
getattr(st, kind)(text)

r1c1, r1c2 = st.columns(2)
# Delta immer als „mein Wert minus Referenz“; die Farbe regelt delta_color="inverse" (Vorzeichen-Falle, DEMO-PLAYBOOK §2). Referenz: die kürzeste Lösung (f = 0).
r1c1.metric(f"Fahrzeuge bei f = {settings.fix}", f"{sel.vehicles}", delta=f"{sel.vehicles - f0.vehicles:+d} gegen die kürzeste Lösung", delta_color="inverse")
r1c2.metric("Distanz (Längeneinheiten)", E.km(sel.dist), delta=f"{R.num((sel.dist - f0.dist) / M.SCALE, 1, True)} gegen die kürzeste Lösung", delta_color="inverse")
r2c1, r2c2 = st.columns(2)
r2c1.metric(f"Gesamtkosten f · V + D bei f = {settings.fix}", R.num(E.cost(sel, settings.fix), 1),
            delta=f"{R.num(E.cost(sel, settings.fix) - E.cost(f0, settings.fix), 1, True)} gegen die kürzeste Lösung", delta_color="inverse")
r2c2.metric("Auslastung der Fahrzeuge", f"{R.num(E.utilisation(a.inst, sel))} %", delta=f"{R.num(E.utilisation(a.inst, sel) - E.utilisation(a.inst, f0), 1, True)} Prozentpunkte gegen die kürzeste Lösung", delta_color="off")

mc = st.columns(3)
for col, s in zip(mc, (f0, sel, f400)):
    with col:
        st.plotly_chart(VIZ.build_map(a.inst, s.routes, f"{s.label}: {s.vehicles} Fahrzeuge, Distanz {E.km(s.dist)}"), width="stretch", key=f"map_{s.key}")
st.caption(f"Kapazität Q = {a.inst.Q} bei Gesamtmenge {sum(a.inst.dem)} (untere Schranke der Fahrzeugzahl ⌈Σd / Q⌉ = {M.lower_bound_vehicles(a.inst)}). Punktgröße = Menge, Stern = Depot, jede Farbe ein Fahrzeug. "
           f"Rechenzeit der drei Läufe auf diesem Rechner: {R.num(a.seconds, 1)} s.")
st.plotly_chart(VIZ.build_cost_lines(a.sols, settings.fix), width="stretch", key="cost_chart")
st.caption("Gesamtkosten f · V + D der Lösungen dieser Instanz über den Fixkosten f; die Linien kreuzen sich beim Kipppunkt. Gleiche Lösungen (gleiche Fahrzeugzahl und Distanz) erscheinen nur einmal.")
st.download_button("📄 Tourenplan als PDF", data=build_pdf(settings, a, "sel"), file_name="fahrzeuggroesse.pdf", mime="application/pdf", key="pdf_download")

st.markdown("---")

# --- Kernfrage 1: Wann gibt es einen Zielkonflikt? ---------------------------------------------------------------------------------------------

st.markdown("## ❓ Kernfrage 1: Wann gibt es einen Zielkonflikt?")
kind, text = E.verdict_hebel()
getattr(st, kind)(text)
c1, c2 = st.columns([3, 2])
with c1:
    st.plotly_chart(VIZ.build_cell_map((settings.n, settings.depot, settings.k, settings.reserve)), width="stretch", key="cell_chart")
    st.caption("Zellenkarte: ΔV = Mittel von V(f = 0) − V(f = 400) über 25 Instanzen. Rot: ab 0,3 (Zielkonflikt), orange: dazwischen, grau: unter 0,1 (kein Zielkonflikt). Schwarzer Rahmen: die gewählte Einstellung.")
with c2:
    st.plotly_chart(VIZ.build_v_lines(), width="stretch", key="v_chart")
    ve = {s: R.by_reserve(s)["Vf_excess"] for s in C.RESERVE_OPTIONS}
    st.caption("Mittlere Zahl Fahrzeuge über der unteren Schranke ⌈Σd / Q⌉ je Fixkosten, je Reserve (Instanzen mit 3 oder 5 Ladungen, je 200). Von f = 0 auf f = 400 fällt die Linie "
               + ", ".join(f"bei {R.num(100 * s, 0)} % Reserve von {R.num(ve[s][0], 2)} auf {R.num(ve[s][-1], 2)}" for s in C.RESERVE_OPTIONS) + ".")
fac = R.load()["factors"]
st.markdown(
    "Anteil der Zielkonflikt-Zellen je Stufe der Faktoren (32 Zellen): " + ", ".join(f"{R.num(100 * float(lv), 0)} % Reserve: {R.pct(v['share'])} %" for lv, v in fac["s"].items())
    + f"; Ladungen 3: {R.pct(fac['k']['3']['share'])} %, 5: {R.pct(fac['k']['5']['share'])} %; Kunden 20: {R.pct(fac['n']['20']['share'])} %, 40: {R.pct(fac['n']['40']['share'])} %; "
    f"Depot Rand: {R.pct(fac['depot']['rand']['share'])} %, Mitte: {R.pct(fac['depot']['mitte']['share'])} %."
)
d0 = R.by_reserve(0.0)
st.markdown(
    "**Was dahintersteckt (Deutung aus den Zählungen, nicht gesondert gemessen):** Je knapper der Laderaum, desto schwerer ist es, alle Mengen in ⌈Σd / Q⌉ Fahrzeuge zu packen, und desto öfter ist die kürzeste Lösung eine mit einem Fahrzeug mehr. "
    + "Die kürzeste Lösung nutzt im Mittel " + ", ".join(f"{R.num(R.by_reserve(s)['excess0'], 2)}" for s in C.RESERVE_OPTIONS)
    + " Fahrzeuge über der unteren Schranke (Reserve 0 / 2 / 5 / 10 %, je 200 Instanzen mit 3 oder 5 Ladungen). Ab 5 % Reserve fand die Suche in der Messreihe in "
    + f"{R.by_reserve(0.05)['n_front_inst'] + R.by_reserve(0.1)['n_front_inst']} von {R.by_reserve(0.05)['m'] + R.by_reserve(0.1)['m']} Instanzen eine Lösung mit weniger Fahrzeugen bei f = 400."
)
rows = []
for s in C.RESERVE_OPTIONS:
    for kk in C.K_OPTIONS:
        d = R.by_reserve(s)["per_k"][str(kk)]
        rows.append({"Reserve": f"{R.num(100 * s, 0)} %", "Ladungen": kk, "Instanzen mit weniger Fahrzeugen bei f = 400": f"{d['n_front_inst']} von {d['m']}", "mittleres ΔV": d["dV"],
                     "Distanz bei f = 400 gegen f = 0 (alle Instanzen, %)": d["dD_all"], "Erste Stufe mit weniger Fahrzeugen (Instanzen bei 10 / 25 / 50 / 100 / 200 / 400)": R.fstar_counts_text(d["fstar_counts"])})
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
             column_config={"mittleres ΔV": st.column_config.NumberColumn(format="%.2f"), "Distanz bei f = 400 gegen f = 0 (alle Instanzen, %)": st.column_config.NumberColumn(format="%.2f")})
mx_v = max(c["max_distinct_V"] for c in R.cells(False))
st.caption("Kennzahlen aus 100 Instanzen je Zeile (Zufalls-Seeds 300000 bis 300024, beide Depots, 20 und 40 Kunden). Auf den sieben Fixkostenstufen kommen in keiner der "
           f"{R.load()['meta']['rows_m1']} Instanzzeilen mehr als {mx_v} verschiedene Fahrzeugzahlen vor" + (": die Front ist eine Stufe, keine Kurve." if mx_v == 2 else "."))

st.markdown("---")

# --- Kernfrage 2: Was kostet ein Fahrzeug weniger? ---------------------------------------------------------------------------------------------

st.markdown("## ❓ Kernfrage 2: Was kostet ein Fahrzeug weniger?")
c1, c2 = st.columns(2)
with c1:
    st.plotly_chart(VIZ.build_reserve_bars(), width="stretch", key="reserve_chart")
    st.caption("Anteil der Instanzen, in denen die Lösung bei f = 400 weniger Fahrzeuge hat als bei f = 0, je Reserve und Ladungen (je 100 Instanzen).")
with c2:
    st.plotly_chart(VIZ.build_fstar_bars(), width="stretch", key="fstar_chart")
    st.caption("Erste gemessene Fixkostenstufe (10, 25, 50, 100, 200, 400), bei der die Fahrzeugzahl unter die bei f = 0 sinkt, je Instanz; das ist eine Obergrenze des rechnerischen Kipppunkts f*. Gezählt sind nur die Instanzen, in denen sie sinkt.")
parts = []
for s in C.RESERVE_OPTIONS:
    d = R.by_reserve(s)
    if d["n_front_inst"] >= 4:
        parts.append(f"Reserve {R.num(100 * s, 0)} %: rechnerischer Kipppunkt {R.fpair_text(d)}, {d['n_front_inst']} Instanzen, die Lösung bei f = 400 ist dort im Mittel {R.num(d['price_mean'])} % länger")
    elif d["n_front_inst"] > 0:
        parts.append(f"Reserve {R.num(100 * s, 0)} %: {d['n_front_inst']} Instanzen mit weniger Fahrzeugen, im Mittel {R.num(d['price_mean'])} % länger")
    else:
        parts.append(f"Reserve {R.num(100 * s, 0)} %: keine Instanz mit weniger Fahrzeugen")
st.markdown("**Rechnerischer Kipppunkt f\\* = (D₄₀₀ − D₀) / (V₀ − V₄₀₀) und Preis der Fahrzeug-Ersparnis** (nur Instanzen, in denen die Fahrzeugzahl bei f = 400 sinkt; D₀ und V₀ gehören zur Lösung bei f = 0, D₄₀₀ und V₄₀₀ zu der bei f = 400): " + "; ".join(parts) + ". "
            f"Darunter {sum(c['n_same_dist'] for c in R.cells(False))} Instanzen mit weniger Fahrzeugen, deren Distanz nicht länger ist (dort ist f* = 0).")
orc0 = R.load()["orakel"]["0.0"]
st.warning("**Die Höhe der Front bei Reserve 0 % ist die der Suche.** Die eigene Suche ist kein Optimum. Das exakte Verfahren gibt es nur bis 12 Kunden: dort (k = 3, Reserve 0, 2 und 10 %; 5 % nicht gerechnet) liegt die Kostenlücke der Suche bei Reserve 0 % im Mittel "
           f"{R.num(orc0['gap_mean'], 3)} % ({orc0['n_over_half']} von {orc0['cases']} Fällen über 0,5 %, größte {R.num(orc0['gap_max'])} %; die {orc0['cases']} Fälle sind {orc0['instances']} Instanzen × 7 Stufen und nicht unabhängig"
           f"{', die Fälle über 0,5 % stammen aus ' + str(orc0['instances_over_half']) + ' Instanz' + ('en' if orc0['instances_over_half'] != 1 else '') if orc0['n_over_half'] else ''}). "
           "Das Orakel misst die Kostenlücke, nicht die Höhe des Zielkonflikts; ob die Suche bei 20 und 40 Kunden die Front ebenso trifft, ist nicht gemessen. Die Aussage „kein Zielkonflikt ab 5 % Reserve“ ist robuster als die Höhe darunter.")

st.markdown("---")

# --- Kernfrage 3: Was sagt die Formel voraus? --------------------------------------------------------------------------------------------------

st.markdown("## ❓ Kernfrage 3: Welche Distanz sagt die Formel voraus?")
fm = R.load()["formel"]
st.markdown(
    "Struktur einer Kontinuumsnäherung (Daganzo; Konstanten und Gültigkeitsbedingungen der Literatur nicht nachgeprüft): **D(Q) ≈ a · 2 · r̄ · Σd / Q + b · √(n · A)**. Der erste Summand ist die Strecke zwischen Depot und Gebiet "
    "(jede Ladung fährt hin und zurück, r̄ = mittlerer Abstand Kunde–Depot), der zweite die Strecke im Gebiet (A = Gebietsfläche). **a und b sind hier angepasst, nicht übernommen.**"
)
kind, text = E.verdict_formel()
getattr(st, kind)(text)
c1, c2 = st.columns([3, 2])
with c1:
    st.plotly_chart(VIZ.build_error_map(), width="stretch", key="error_chart")
    st.caption(f"Fehlerkarte: mittlerer Betrag der relativen Abweichung der Formel von der gelösten Distanz je Zelle (Reserve {R.num(100 * C.FORMEL_RESERVE, 0)} %, f = 0, je 25 Instanzen). "
               f"Angepasst wurde auf {fm['n_fit']} Lösungen mit anderen Zufalls-Seeds (1000 bis 1011) als die der Messung.")
with c2:
    st.markdown(
        f"Getestet wurde die Formel in denselben {len(fm['cells'])} Zellen (20 und 40 Kunden, beide Depots, k = 2, 3, 5, 8, Reserve 10 %, f = 0), an denen angepasst wurde, nur mit anderen Zufalls-Seeds; "
        f"gegen die Lösung der eigenen Suche, nicht gegen das Optimum. Je Instanz liegt der Fehler im Mittel bei {R.num(fm['inst_err_mean'])} %, höchstens bei {R.num(fm['inst_err_max'])} %; "
        f"{fm['inst_over10']} von {fm['inst_n']} Instanzen erreichen 10 % oder mehr. Der Zellfehler enthält einen Bias zwischen {R.num(fm['bias_min'])} und {R.num(fm['bias_max'], 1, True)} % (Formel unter bzw. über der Suchlösung). "
        "Für andere Reserven, Kundenzahlen oder Gebiete ist die Formel nicht getestet."
    )

st.markdown("---")

# --- Methodenvergleich ---------------------------------------------------------------------------------------------------------------------

with st.expander("🔧 Wie wir das erreichen – vollständiger Methodenvergleich"):
    tab_tours, tab_front, tab_formula, tab_or, tab_series = st.tabs(["🚚 Touren", "🔎 Front", "🧮 Formel", "🤖 OR-Tools", "📈 Messreihe"])
    with tab_tours:
        rows = [{"Lösung": s.label, "Fahrzeuge": s.vehicles, "Distanz": s.dist / M.SCALE, f"Gesamtkosten bei f = {settings.fix}": E.cost(s, settings.fix),
                 "Auslastung (%)": E.utilisation(a.inst, s)} for s in a.sols]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                     column_config={"Distanz": st.column_config.NumberColumn(format="%.1f"), f"Gesamtkosten bei f = {settings.fix}": st.column_config.NumberColumn(format="%.1f"),
                                    "Auslastung (%)": st.column_config.NumberColumn(format="%.1f")})
        st.caption("Distanz in Längeneinheiten des 100 × 100-Gebiets. Die drei Lösungen kommen aus einer Kette von Suchen (je eine bei f = 0, bei dem gewählten f und bei f = 400, aufsteigend, mit den Lösungen der kleineren f als zusätzlichem Start); "
                   "die Messreihe rechnet sieben Fixkostenstufen in zwei Durchgängen (aufsteigend und absteigend).")
        view = st.selectbox("Halteliste anzeigen für", [s.key for s in a.sols], index=1, format_func=lambda key: E.sol_of(a, key).label, key="view_select",
                            help="Reine Anzeigewahl: ändert nichts an der Rechnung.")
        for ri, route in enumerate(E.sol_of(a, view).routes):
            load = sum(a.inst.dem[c_] for c_ in route)
            st.caption(f"Tour {ri + 1}: Länge {E.km(M.route_len(a.inst.D, list(route)))}, Last {load} von {a.inst.Q}, Stopps {', '.join(str(c_) for c_ in route)}")
        st.markdown(
            "- **Eigene Suche:** Ruin-and-Recreate (zufällige, benachbarte oder ganze Touren herausnehmen und billigst wieder einfügen) mit Relocate, Swap, 2-opt, 2-opt\\*, Verschmelzen zweier Touren; die Fixkosten stehen im Einfügepreis. Annahme nach Record-to-Record (0,4 %).\n"
            "- **Start:** Clarke-Wright (Savings); bei knapper Kapazität, wenn Savings mehr Fahrzeuge braucht als ⌈Σd / Q⌉, zusätzlich ein **Packungsstart**: eine deterministische Tiefensuche, die die Mengen auf ⌈Σd / Q⌉ Behälter verteilt (feste Knotengrenze, nur Ganzzahlen).\n"
            "- **Warum nötig:** Bei der Vorbereitung der Vormessung (mit dem früheren Packungsstart, nicht neu gemessen) fand die Suche allein bei knapper Kapazität die Fahrzeugzahl bei mittlerem f nicht stabil (die Distanz bei V = 3 fiel mit größerem f).\n"
            "- **Kette:** Für jedes f zählt die billigste aller bei den drei (live) bzw. 14 (Messreihe) Suchen gefundenen Lösungen, auch von anderen f; die „kürzeste Lösung“ kann also bei einem höheren f gefunden worden sein."
        )
    with tab_front:
        st.markdown(f"Die Zelle dieser Einstellung ({E.cell_text(cell)}): Mittel über {cell['m']} Instanzen je Fixkostenstufe.")
        df = pd.DataFrame({"f": list(C.FIX_OPTIONS), "Fahrzeuge (Mittel)": cell["Vf"], "Distanz (Mittel)": [x / M.SCALE for x in cell["Df"]],
                           "Instanzen mit weniger Fahrzeugen als bei f = 0": [0] + [cell["n_less_at_f"][str(f)] for f in C.FIX_OPTIONS[1:]]})
        st.dataframe(df, hide_index=True, width="stretch", column_config={"Fahrzeuge (Mittel)": st.column_config.NumberColumn(format="%.2f"), "Distanz (Mittel)": st.column_config.NumberColumn(format="%.1f")})
        st.caption(f"Untere Schranke ⌈Σd / Q⌉ im Mittel {R.num(cell['vmin'], 2)} Fahrzeuge. Erste Stufe mit weniger Fahrzeugen in dieser Zelle (Instanzen bei 10 / 25 / 50 / 100 / 200 / 400): {R.fstar_counts_text(cell['fstar_counts'])}."
                   + (f" Rechnerischer Kipppunkt f* = (D₄₀₀ − D₀) / (V₀ − V₄₀₀): {R.fpair_text(cell)}." if cell["fpair_median"] is not None and cell["fpair_quartiles"] else ""))
    with tab_formula:
        st.markdown(
            f"Die Formel für **diese Instanz**: D̂(Q) = a · 2 · r̄ · Σd / Q + b · √(n · A) mit a = {R.num(fm['a'], 3)}, b = {R.num(fm['b'], 3)}, r̄ = {R.num(M.depot_dist_mean(a.inst) / M.SCALE)}, "
            f"Σd = {sum(a.inst.dem)}, n = {a.inst.n}. Vier Läufe (k = 2, 3, 5, 8 bei {R.num(100 * C.FORMEL_RESERVE, 0)} % Reserve, f = 0) setzen gelöste Punkte neben die Kurve."
        )
        if st.button(f"Vier Punkte rechnen (4 Suchen mit {settings.ils} Iterationen)", key="formula_start"):
            st.session_state["formula_done"] = settings
            st.rerun()
        pts = None
        if st.session_state.get("formula_done") == settings:
            with st.spinner("Rechne vier Suchen ..."):
                pts = _formula_points(settings)
        st.plotly_chart(VIZ.build_formula_curve(a.inst, fm["a"], fm["b"], pts), width="stretch", key="formula_chart")
        if pts:
            table = [(kk, q, d, FO.predicted_distance(a.inst, q, fm["a"], fm["b"])) for kk, q, d in pts]
            kind, text = E.verdict_formel_instanz(a.inst, (fm["a"], fm["b"]), table)
            getattr(st, kind)(text)
        st.markdown("**Größenwahl** (Nachmessung, nicht Teil der Hauptaussage): Gesucht ist die beste Fahrzeuggröße unter einer Kostenannahme. Es gibt vier Größen k = 2, 3, 5, 8 (Reserve 10 %); Kostenfamilie: Fixkosten **und** Kilometerkosten je Fahrzeug "
                    "wachsen mit q^σ, q = Q / Q_ref (Q_ref = Q bei k = 2, f gilt für diese Größe). σ < 1 bedeutet Größenvorteil, σ > 1 Größennachteil. „Innere Stufe“ heißt k = 3 oder 5. "
                    "Verglichen wird die beste Größe, die aus den gelösten Instanzen folgt, mit der, die die Formel wählt (Fahrzeugzahl ⌈Σd / Q⌉, Distanz aus der Formel).")
        qrows = [{"σ": q["sigma"], "f": q["f"], "Fälle": q["cases"], "innere Stufe (k = 3 oder 5) ist die beste": q["inner"], "Formel trifft dieselbe Stufe": q["hit_all"],
                  "davon bei innerer Stufe": q["hit_inner"], "beste konstante Wahl trifft": q["const_hit"], "höchstens eine Stufe daneben": q["near"]} for q in R.load()["qstern"] if q["f"] in (25, 100)]
        st.dataframe(pd.DataFrame(qrows), hide_index=True, width="stretch")
        st.caption("100 Fälle je Zeile (25 Instanzen × 2 Kundenzahlen × 2 Depots); gemessen sind σ = 0,4, 0,5, 1, 1,5 und 2 (kleinere σ nicht) mit f = 25, 50, 100 und 200, die Tabelle zeigt f = 25 und 100. „Beste konstante Wahl“ ist die Zahl der Fälle, in denen die am häufigsten beste Größe "
                   "die beste ist: Wer immer dieselbe Größe wählt, trifft so oft; ein Treffer der Formel zählt erst darüber. "
                   "Für σ ≥ 1 ist in allen gemessenen Fällen das kleinste Fahrzeug (k = 8) das billigste, bei Messung und Formel: dort ist „Formel trifft dieselbe Stufe“ trivial. "
                   "Eine innere Stufe als beste gibt es in der Messung nur bei σ = 0,4 und 0,5 und nicht bei f = 200; wo es sie gibt, trifft die Formel sie nicht immer (Spalte „davon bei innerer Stufe“), und bei f = 100 wählt sie fast immer k = 2.")
    with tab_or:
        secs = C.ORTOOLS_SECONDS[settings.n]
        st.markdown(f"OR-Tools (Routing, Guided Local Search) mit Fixkosten je Fahrzeug bei dem gewählten f, in zwei Einstellungen, je {secs} s: **Standard** (Erststrategie PATH_CHEAPEST_ARC) und **SAVINGS**; höchstens ⌈Σd / Q⌉ + 4 Fahrzeuge.")
        if st.button(f"OR-Tools rechnen (2 × {secs} s)", key="ortools_start"):
            st.session_state["ortools_done"] = settings
            st.rerun()
        if st.session_state.get("ortools_done") == settings:
            with st.spinner(f"OR-Tools rechnet (2 Läufe à {secs} s) ..."):
                try:
                    res = _ortools(settings)
                except ImportError:
                    res = None
                    st.warning("OR-Tools ist in dieser Umgebung nicht installiert.")
            if res is not None:
                kind, text = E.verdict_ortools(E.cost(sel, settings.fix), res, secs)
                getattr(st, kind)(text)
        ort = R.load()["ort"]
        bo = ort["best_of_two"]
        so = ort["secs_ort"]
        os_ = ort["own_secs_per_stage"]
        st.caption(f"Messreihe ({ort['runs']} Läufe, die ersten 5 Instanzen je Zelle, f = 0, 25, 100, 400; darunter die 8 Zellen mit k = 2 und 8): OR-Tools bekam je Fixkostenstufe {R.num(float(so['20']), 0)} s (20 Kunden) bzw. {R.num(float(so['40']), 0)} s (40 Kunden) je Einstellung, "
                   f"die Zahl „bessere der beiden Einstellungen“ also das Doppelte; die eigene Kette brauchte im Mittel {R.num(os_['20'], 1)} s bzw. {R.num(os_['40'], 1)} s je Fixkostenstufe (zwei Suchen, unter Last mit sechs parallelen Prozessen gemessen) und nimmt je f die billigste aus allen ihren Läufen. "
                   f"Gleiche Rechenzeit wurde nicht gemessen; eine Obergrenze oder Rangfolge der Löser folgt daraus nicht. Je Lauf die bessere der beiden Einstellungen {R.num(bo['mean'], 2, True)} % gegen die eigene Suche, aber in {bo['equal']} von {bo['runs']} Läufen gleich "
                   f"(Median {R.num(bo['median'], 1)} %, {bo['over1']} Läufe über 1 %, {bo['over5']} über 5 %, größte {R.num(bo['max'], 1, True)} %; OR-Tools besser in {bo['better']} Läufen).")
    with tab_series:
        st.markdown("Alle 40 Zellen des Hauptrasters (je 25 Instanzen, Zufalls-Seeds 300000 bis 300024, eigene Suche mit 400 Iterationen, Fixkosten 0 bis 400); die Zellen mit 3 oder 5 Ladungen sind die 32 der Zellenkarte.")
        rows = []
        for c_ in R.cells(False):
            rows.append({"Zelle": c_["ci"], "Kunden": c_["n"], "Depot": "Rand" if c_["depot"] == "rand" else "Mitte", "Ladungen": c_["k"], "Reserve (%)": round(100 * c_["s"]), "Q (Mittel)": c_["Q"],
                         "ΔV": c_["dV"], "Klasse": R.KLASS_LABEL[c_["klass"]] if c_["ampel"] else "–", "Instanzen mit weniger Fahrzeugen": c_["n_front_inst"],
                         "rechnerischer Kipppunkt f* (Median)": c_["fpair_median"], "Distanz bei f = 400 (%)": c_["dD_all"], "Fahrzeuge über Schranke bei f = 0": c_["excess0"]})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                     column_config={"ΔV": st.column_config.NumberColumn(format="%.2f"), "Distanz bei f = 400 (%)": st.column_config.NumberColumn(format="%.2f"), "rechnerischer Kipppunkt f* (Median)": st.column_config.NumberColumn(format="%.1f"),
                                    "Fahrzeuge über Schranke bei f = 0": st.column_config.NumberColumn(format="%.2f"), "Q (Mittel)": st.column_config.NumberColumn(format="%.0f")})
        orc = R.load()["orakel"]
        st.markdown(
            f"**Eigene Suche gegen das exakte Optimum (12 Kunden, k = 3, Reserve 0, 2 und 10 %; 5 % nicht gerechnet; {orc['0.0']['instances']} Instanzen × 7 Fixkostenstufen = {orc['0.0']['cases']} Fälle je Reserve, nicht unabhängig):** mittlere Kostenlücke bei Reserve 0 % {R.num(orc['0.0']['gap_mean'], 3)} % "
            f"({orc['0.0']['n_over_half']} von {orc['0.0']['cases']} Fällen über 0,5 %, größte {R.num(orc['0.0']['gap_max'])} %, die Fälle über 0,5 % aus {orc['0.0']['instances_over_half']} Instanz), bei 2 % {R.num(orc['0.02']['gap_mean'], 3)} % und bei 10 % {R.num(orc['0.1']['gap_mean'], 3)} %. "
            f"Das ist die Kette der Messreihe (sieben Stufen, zwei Durchgänge). Mit einem Durchgang über die sieben Stufen (so rechnete die Vormessung) {R.num(orc['0.0']['pass1_gap_mean'], 3)} % ({orc['0.0']['pass1_n_over_half']} Fälle über 0,5 % aus {orc['0.0']['pass1_instances_over_half']} Instanzen). "
            f"Die Live-Kette der App (drei Stufen f = 0, 100, 400, ein Durchgang) liegt über diese {orc['0.0']['live_cases']} Fälle bei {R.num(orc['0.0']['live_gap_mean'], 3)} %; die Kette der Messreihe auf denselben {orc['0.0']['live_cases']} Fällen bei {R.num(orc['0.0']['chain48_gap_mean'], 3)} %. "
            "Das Orakel misst die Kostenlücke, nicht die Höhe des Zielkonflikts."
        )
        vm = R.load()["vormessung"]
        st.markdown(
            "**Aus der Vormessung (nicht neu gerechnet; dort war der Packungsstart noch ein CP-SAT-Lauf):** 400 gegen 1 500 Iterationen auf drei Bedingungen: mittlere Mehrkosten "
            f"{R.num(vm['abstimmung_400_gegen_1500']['mehrkosten_mittel'], 2)} % (größte {R.num(vm['abstimmung_400_gegen_1500']['mehrkosten_max'], 2)} %, {vm['abstimmung_400_gegen_1500']['laeufe']} Läufe); "
            f"Kontrolle auf {vm['kontrolle_1500']['zellen']} Zellen mit 1 500 Iterationen: Fahrzeugzahl in {vm['kontrolle_1500']['fahrzeugzahl_verschieden']} von {vm['kontrolle_1500']['werte']} Werten verschieden, "
            f"Zellen mit Zielkonflikt {vm['kontrolle_1500']['front_zellen_400']} gegen {vm['kontrolle_1500']['front_zellen_1500']}."
        )
        mg = R.load()["mengen"]
        st.markdown("**Andere Mengenverteilungen** (je 8 Instanzen, Zufalls-Seeds 310000 bis 310007, vier Fixkostenstufen 0, 25, 100, 400; eine Zelle ist Kunden × Depot × Ladungen, je Reserve 8 Zellen, also 3 × 32 = 96 Zellen für die drei anderen Verteilungen und 32 für die Kontrolle „gleich 5 bis 25“): Zielkonflikt-Zellen je Reserve 0 / 2 / 5 / 10 %; eine Zelle gilt bei ΔV ≥ 0,3 als Zielkonflikt, bei acht Instanzen also ab drei mit weniger Fahrzeugen.")
        mrows = []
        for dist, label in (("gleich", "gleich 5 bis 25 (wie das Hauptraster)"), ("weit", "weit 1 bis 40"), ("schief", "schief (80 % 3 bis 10, 20 % 25 bis 45)"), ("fast", "fast gleich 14 bis 16")):
            mrows.append({"Mengen": label, **{f"Reserve {R.num(100 * s, 0)} %": f"{mg[dist][str(s)]['front_cells']} von {mg[dist][str(s)]['cells']}" for s in C.RESERVE_OPTIONS}})
        st.dataframe(pd.DataFrame(mrows), hide_index=True, width="stretch")

with st.expander("Wie funktioniert diese Demo?"):
    vm = R.load()["vormessung"]
    rc0, rc2, rc5, rc10 = (R.reserve_counts(s) for s in C.RESERVE_OPTIONS)
    mg_front0 = [R.load()["mengen"][d]["0.0"]["front_cells"] for d in ("weit", "schief", "fast")]
    MG_LO, MG_HI = min(mg_front0), max(mg_front0)
    EK, EI = vm["erkundung"]["seeds"], vm["erkundung"]["iterationen"]
    MX = {k_: R.num(v_, 2) for k_, v_ in vm["mix_n12"].items() if k_.startswith("gegen")}
    MG_5 = max(R.load()["mengen"][d]["0.05"]["front_cells"] for d in ("weit", "schief", "fast"))
    MG_10 = max(R.load()["mengen"][d]["0.1"]["front_cells"] for d in ("weit", "schief", "fast"))
    st.markdown(
        f"""
**Die Aufgabe.** Ein Depot, {settings.n} Kunden im 100 × 100-Gebiet mit Mengen von 5 bis 25 (gleichverteilt, ganzzahlig), unbegrenzt viele gleiche Fahrzeuge mit Kapazität Q = {a.inst.Q}, euklidische Entfernungen auf 0,1 Längeneinheiten gerundet.
Jedes genutzte Fahrzeug kostet f (in Längeneinheiten), jede gefahrene Längeneinheit kostet 1; Ziel sind die **Gesamtkosten f · V + D** (V Fahrzeuge, D Gesamtdistanz). Die Kapazität folgt aus den **Ladungen k** und der **Reserve**:
Q = max(⌈(1 + Reserve) · Σd / k⌉, größte Einzelmenge), die Mindestzahl Fahrzeuge ist also etwa k.

**Front und Kipppunkt.** Zu jedem f gehört die beste gefundene Lösung mit V(f) Fahrzeugen und D(f) Distanz; mit wachsendem f sinkt V (im Mittel nicht steigend, getestet). Der **rechnerische Kipppunkt** zweier Lösungen mit V₀ > V₁ ist
f\\* = (D₁ − D₀) / (V₀ − V₁); die Tabellen nennen ihn aus den Lösungen bei f = 0 und f = 400 und zusätzlich die erste Fixkostenstufe, bei der die Fahrzeugzahl sinkt (eine Obergrenze). Eine **Zelle** ist eine Kombination aus Kundenzahl, Depot, Ladungen und Reserve; sie ist **Zielkonflikt**, wenn das Mittel ΔV = V(f = 0) − V(f = 400) mindestens {R.num(C.FRONT_DV, 1)} beträgt, und **kein Zielkonflikt**, wenn es unter {R.num(C.KEINE_DV, 1)} liegt. Die Fahrzeugzahl sinkt nie um mehr als eins (die Front hat höchstens zwei Stufen), ΔV ist darum zugleich der Anteil der Instanzen, in denen sie sinkt.

**Was die Live-Zahlen bedeuten.** Sie gelten für diese eine Instanz. Die Aussagen der Kernfragen stammen aus einer vorgerechneten Messreihe (40 Zellen, je 25 Instanzen, Zufalls-Seeds ab 300000, eigene Suche mit 400 Iterationen, sieben Fixkostenstufen in zwei Durchgängen);
alle Regler stehen auf gemessenen Stufen, zu jeder Einstellung gehört also eine Zelle. Von den {R.load()['n_amp']} Zellen mit 3 oder 5 Ladungen sind {R.klass_counts()['front']} Zielkonflikt, {R.klass_counts()['keine']} kein Zielkonflikt und {R.klass_counts()['zwischen']} Grenzfälle:
bei 0 % Reserve {rc0['front']} von {rc0['zellen']} Zielkonflikt, bei 2 % {rc2['front']}, bei 5 % {rc5['front']}, bei 10 % {rc10['front']}.

**Warum eine Reserve? (Deutung, nicht gesondert gemessen)** Bei knapper Kapazität liegt ein Packproblem nahe: Die Mengen müssen fast exakt in k Fahrzeuge passen, und die kürzeste Lösung nutzt dann im Mittel {R.num(R.by_reserve(0.0)['excess0'], 2)} Fahrzeuge mehr als die untere Schranke; bei 10 % Reserve sind es {R.num(R.by_reserve(0.1)['excess0'], 2)}.

**Nicht Teil der Demo: Flottenmix.** Zwei Fahrzeuggrößen gleichzeitig (ein kleines und ein großes Fahrzeug) wurden gemessen, aber nicht belegt: Die Suche hat keine Züge, die gezielt gemischte Flotten bilden; bei 12 Kunden (Vormessung, nicht neu gerechnet; nur σ = 1, Kapazitätspaar k = 8 und 3, f = 100, 24 Instanzen) liegt der exakte Mix im Mittel {MX['gegen_beste_einheitsflotte']} % unter der besten der vier Einheitsflotten
({MX['gegen_bessere_des_paares']} % unter der besseren der beiden des Paares); bei 20 und 40 Kunden ist der Vorteil unbekannt. Ob ein besserer Löser lohnt, ist eine offene Frage.

**🚧 Wo die Annahmen enden**

| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| Mengen gleichverteilt 5 bis 25 | „Knappe Kapazität“ heißt hier Packen nahe an 100 % Auslastung. In drei anderen Mengenverteilungen (weit 1 bis 40, schief, fast gleich) gilt „kein Zielkonflikt ab 5 % Reserve“ nicht ganz: bei 5 % Reserve höchstens {MG_5} von 8 Zellen mit Zielkonflikt, bei 10 % höchstens {MG_10}; die Höhe des Zielkonflikts bei 0 % Reserve schwankt ({MG_LO} bis {MG_HI} von 8 Zellen). Praxisdaten sind nicht gemessen | Tab Messreihe |
| Die Front ist die der Suche | Die eigene Suche ist kein Optimum; bei 12 Kunden und Reserve 0 % liegt sie im Mittel {R.num(R.load()['orakel']['0.0']['gap_mean'], 3)} % über dem exakten Wert. Die Höhe der Front bei Reserve 0 % ist darum schwächer belegt als „kein Zielkonflikt ab 5 %“ | Kernfrage 2 |
| Reserve als Hauptfaktor | Die Wahl der Reserve als Hauptfaktor des Rasters und die Schwellen (0,1 und 0,3 für ΔV, 60 und 20 % für „trennt“) entstanden nach einer Erkundung auf anderen Zufalls-Seeds ({EK[0]} bis {EK[1]}, n = 20 und 40, Depot Rand, {EI} Iterationen); die Messung selbst kam danach. Die Reserve hat vier, die anderen Faktoren haben zwei Stufen | Kernfrage 1 |
| Ein Fahrzeugtyp, unbegrenzt viele Fahrzeuge | Kein Flottenmix (nicht belegt), keine begrenzte Fahrzeugzahl | nicht gemessen |
| Zufallsinstanzen, euklidisch, keine Zeitfenster, keine Servicezeit | Zeitfenster und echte Straßennetze verändern die Packbarkeit; nicht gemessen | Ausbau |
| Nur 20 und 40 Kunden | Für größere Instanzen keine Aussage; die Formel ist nur in 16 Zellen (20 und 40 Kunden, Reserve 10 %, f = 0) getestet | Kernfrage 3 |
| Formel: a und b angepasst | Konstanten und Gültigkeitsbedingungen der Literatur sind nicht nachgeprüft; die Anpassung gilt für diesen Generator, getestet in denselben Zellen mit anderen Zufalls-Seeds | Kernfrage 3 |
| OR-Tools | Im Mittel über der eigenen Suche (in einem Teil der Läufe gleich) bei 3 s bzw. 6 s je Einstellung; die eigene Kette brauchte je Fixkostenstufe weniger Zeit, gleiche Zeit ist nicht gemessen: keine Rangfolge, keine Obergrenze | Tab OR-Tools |
| Rechenzeiten | Auf anderen Rechnern anders; auf Streamlit Cloud nicht gemessen | Eine Instanz |

**Literatur (nur Zusammenfassungen gelesen, keine Volltexte):** Daganzo 1984, *The length of tours in zones of different shapes* (Transportation Research B 18); Golden, Assad, Levy, Gheysens 1984, *The fleet size and mix vehicle routing problem*
(Computers & Operations Research 11). Die Struktur der Formel (Strecke zum Gebiet plus Strecke im Gebiet) steht in der Übersichtsarbeit arXiv 1706.05448; Zahlenwerte der Konstanten und eine Gültigkeitsbedingung ließen sich dort nicht finden. Die Demo bildet keinen Literaturvergleich.
"""
    )

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Lesehilfe.** Gegeben sind ein Depot $0$, Kunden $N = \{1, \dots, n\}$ mit Mengen $d_i$ und Entfernungen $t_{ij}$, eine Kapazität $Q$ und Fixkosten $f$ je genutztes Fahrzeug. Gesucht sind Touren, die jeden Kunden genau einmal bedienen
und die Gesamtkosten aus Fixkosten und Distanz minimieren; wie viele Fahrzeuge es werden, ist frei.

| Symbol | Bedeutung |
|---|---|
| $N$, $d_i$ | Kunden und ihre Mengen (ganzzahlig 5 bis 25) |
| $Q$ | Kapazität eines Fahrzeugs; $Q = \max\left(\lceil (1 + \rho)\, \sum_i d_i / k \rceil,\ \max_i d_i\right)$ mit Reserve $\rho$ und Ladungen $k$ |
| $t_{ij}$ | ganzzahlige Entfernung von $i$ nach $j$ (euklidisch, Depot $= 0$) |
| $f$ | Fixkosten je genutztes Fahrzeug (Längeneinheiten) |
| $x_{ij}$ | 1, wenn ein Fahrzeug direkt von $i$ nach $j$ fährt |
| $u_i$ | bis einschließlich $i$ ausgelieferte Menge |
        """
    )
    st.markdown(
        """
$$\\min \\; f \\sum_{j \\in N} x_{0j} + \\sum_{i,j \\in N \\cup \\{0\\}} t_{ij}\\, x_{ij}$$

$$\\sum_{j} x_{ij} = 1 \\quad \\text{und} \\quad \\sum_{j} x_{ji} = 1 \\quad (i \\in N)$$

$$u_j = u_i + d_j \\quad \\text{falls } x_{ij} = 1 \\;(i, j \\in N), \\qquad u_j = d_j \\quad \\text{falls } x_{0j} = 1, \\qquad u_i \\le Q$$

Dazu gehören Binärbedingungen für $x$, beliebig viele Abgänge und Rückkehren am Depot (unbegrenzte Flotte, ein Fahrzeugtyp) und ein Teiltourverbot (jeder Kreis enthält das Depot; $u$ erfüllt es). Die Zahl der Fahrzeuge ist
$V = \\sum_j x_{0j}$ und die Distanz $D = \\sum t_{ij} x_{ij}$, die Gesamtkosten also $f V + D$.

**Kipppunkt.** Zwei Lösungen $(V_0, D_0)$ und $(V_1, D_1)$ mit $V_1 < V_0$ und $D_1 > D_0$ haben gleiche Gesamtkosten bei $f^* = (D_1 - D_0) / (V_0 - V_1)$; ab diesem $f$ ist die mit weniger Fahrzeugen billiger.

**Formel.** $\\hat D(Q) = a \\cdot 2 \\bar r \\cdot \\sum_i d_i / Q + b \\sqrt{n A}$ mit $\\bar r$ = mittlerer Abstand Kunde–Depot und $A$ = Gebietsfläche; $a$ und $b$ durch relative kleinste Quadrate angepasst
(Gewicht $1 / D^2$). Die Fahrzeugzahl folgt aus $\\hat V(Q) = \\lceil \\sum_i d_i / Q \\rceil$. Dieser Block ist das vollständige Modell für ein Fahrzeug der Kapazität $Q$; die eigene Suche ist ein Näherungsverfahren und beweist keine Optimalität.
"""
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zum Thema: [Tourenplanung optimieren](https://sebastianhanisch.net/tourenplanung-optimierung.html)."
)
