"""Tourenplan als PDF (fpdf2, Standardschriften). Sonderzeichen werden vorher bereinigt: Gedankenstrich, Minuszeichen, Euro, Anführungszeichen,
Pfeile und Emoji stürzen die Standardschriften sonst ab (DEMO-PLAYBOOK, fpdf2-Falle)."""

from fpdf import FPDF

import fgr_evaluation as E
import fgr_model as M
import fgr_results as R

_REPLACE = {"–": "-", "—": "-", "−": "-", "€": "EUR", "„": '"', "“": '"', "”": '"', "‚": "'", "‘": "'", "’": "'", "→": "->", "×": "x", "±": "+/-",
            "≤": "<=", "≥": ">=", "·": "-", "…": "...", "β": "beta", "Δ": "Delta", "Σ": "Summe", "⌈": "[", "⌉": "]"}


def clean(text: str) -> str:
    """Nur Zeichen der Standardschrift (Latin-1) behalten; bekannte Sonderzeichen ersetzen, Unbekanntes (Emoji) streichen."""
    for old, new in _REPLACE.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "ignore").decode("latin-1")


def build_pdf(settings: E.Settings, a: E.Analysis, sol_key: str = "sel") -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 9, clean("Fahrzeuge oder Kilometer: Tourenplan"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, clean(
        f"{settings.n} Kunden, Depot {E.depot_text(settings.depot)}, {settings.k} Ladungen und {R.num(100 * settings.reserve, 0)} % Reserve (Kapazität {a.inst.Q}, "
        f"Gesamtmenge {sum(a.inst.dem)}), Fixkosten je Fahrzeug {settings.fix}, Zufalls-Seed {settings.seed}, eigene Suche mit {settings.ils} Iterationen."), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Die drei Lösungen dieser Instanz", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 9)
    widths = (66, 24, 32, 36, 30)
    for w, h in zip(widths, ("Lösung", "Fahrzeuge", "Distanz", f"Kosten bei f = {settings.fix}", "Auslastung (%)")):
        pdf.cell(w, 6, clean(h), border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    for s in a.sols:
        for w, v in zip(widths, (s.label, str(s.vehicles), E.km(s.dist), R.num(E.cost(s, settings.fix), 1), R.num(E.utilisation(a.inst, s), 1))):
            pdf.cell(w, 6, clean(v), border=1)
        pdf.ln()
    sol = E.sol_of(a, sol_key)
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, clean(f"Touren: {sol.label} (Distanz {E.km(sol.dist)})"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for ri, route in enumerate(sol.routes):
        stops = " - ".join(f"K{c} ({a.inst.dem[c]})" for c in route)
        load = sum(a.inst.dem[c] for c in route)
        pdf.multi_cell(0, 5, clean(f"Tour {ri + 1} (Länge {E.km(M.route_len(a.inst.D, list(route)))}, Last {load} von {a.inst.Q}): Depot - {stops} - Depot"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(0, 4, clean("Eine Instanz, kein Beleg: die Aussagen der Demo stützen sich auf die vorgerechnete Messreihe "
                               f"({R.load()['meta']['rows_m1']} Instanzzeilen in 40 Zellen, je 25 Instanzen). Distanz in Längeneinheiten des 100 x 100-Gebiets."), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())

