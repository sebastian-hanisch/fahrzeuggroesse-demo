"""Konstanten: Regler-Stufen, feste Annahmen, Farben und Presets.

Alle Regler stehen auf gemessenen Stufen (Hauptraster der Messreihe: 40 Zellen), damit zu jeder Einstellung eine vorgerechnete Zelle gehört."""

N_OPTIONS = (20, 40)
DEFAULT_N = 40
DEPOT_OPTIONS = ("rand", "mitte")
DEFAULT_DEPOT = "mitte"
DEPOT_LABELS = {"rand": "Am Rand (50, 0)", "mitte": "In der Mitte (50, 50)"}
K_OPTIONS = (3, 5)
DEFAULT_K = 5
RESERVE_OPTIONS = (0.0, 0.02, 0.05, 0.10)
DEFAULT_RESERVE = 0.0
FIX_OPTIONS = (0, 10, 25, 50, 100, 200, 400)
DEFAULT_FIX = 50
ILS_OPTIONS = (100, 400)
DEFAULT_ILS = 400
ILS_LABELS = {100: "100 Iterationen (schnell)", 400: "400 Iterationen (wie die Messreihe)"}
MEASURE_ILS = 400                        # Iterationen der eigenen Suche in der vorgerechneten Messreihe
SEED_MAX, DEFAULT_SEED = 999999, 500000  # Messreihen: 1000-1011 (Formel), 2000-2007 (Orakel), 300000-300024 (Hauptraster), 310000-310007 (Mengen)

AREA_SIDE = 100.0                        # Gebiet 100 x 100 Längeneinheiten
DEM_RANGE = (5, 25)                      # Mengen gleichverteilt ganzzahlig 5 bis 25
FIX_MAX = FIX_OPTIONS[-1]                # die Lösung mit den wenigsten gefundenen Fahrzeugen gilt bei f = 400

ORTOOLS_SECONDS = {20: 3, 40: 6}         # Zeitlimit je OR-Tools-Lauf (wie in der Messreihe)
FORMEL_KS = (2, 3, 5, 8)                 # Ladungen der Formel-Punkte (Reserve 10 %)
FORMEL_RESERVE = 0.10

# Klassen der Zellen aus dem Mittel ΔV = V(f = 0) − V(f = 400); Schwellen gesetzt, nicht hergeleitet
FRONT_DV = 0.3                           # ab 0,3: "Zielkonflikt" (Front-Zelle)
KEINE_DV = 0.1                           # unter 0,1: "kein Zielkonflikt"; dazwischen "Grenzfall"
ERR_HOLD = 5.0                           # Formel "hält" in einer Zelle bei mittlerem Fehler bis 5 %

COLOR_F0 = "#2a6fb0"                     # kürzeste gefundene Lösung (f = 0)
COLOR_SEL = "#2a8f5b"                    # Lösung bei dem gewählten f
COLOR_F400 = "#c77700"                   # Lösung bei f = 400 (in 990 von 1000 Instanzen mit der unteren Schranke der Fahrzeugzahl)
COLOR_DEPOT = "#1c2430"
COLOR_FRONT = "#c0392b"
COLOR_ZWISCHEN = "#e2a85a"
COLOR_KEINE = "#9aa5b4"
COLOR_ROUTES = ("#2a6fb0", "#c0392b", "#2a8f5b", "#8a4fb0", "#c77700", "#00897b", "#6d4c41", "#d81b60", "#5c6bc0", "#7cb342", "#f4511e", "#3949ab")
RESERVE_COLORS = {0.0: "#c0392b", 0.02: "#e2a85a", 0.05: "#2a6fb0", 0.10: "#2a8f5b"}

PRESETS = {
    "Standard": {"n": 40, "depot": "mitte", "k": 5, "reserve": 0.0, "fix": 50, "ils": 400, "seed": 500000},
    "Knappe Kapazität, 20 Kunden": {"n": 20, "depot": "mitte", "k": 5, "reserve": 0.0, "fix": 100, "ils": 400, "seed": 500011},
    "Grenzfall: 2 % Reserve": {"n": 20, "depot": "mitte", "k": 3, "reserve": 0.02, "fix": 50, "ils": 400, "seed": 500001},
    "Genug Reserve": {"n": 40, "depot": "rand", "k": 5, "reserve": 0.10, "fix": 50, "ils": 400, "seed": 500011},
    "Wenige Ladungen": {"n": 40, "depot": "mitte", "k": 3, "reserve": 0.0, "fix": 50, "ils": 400, "seed": 500008},
}
PRESET_HELP = {
    "Standard": "40 Kunden, Depot in der Mitte, 5 Ladungen, 0 % Reserve, f = 50: ein Zielkonflikt mittlerer Höhe, nicht der größte der Messreihe (ΔV 0,64; in 16 von 25 Instanzen sinkt die Fahrzeugzahl bis f = 400).",
    "Knappe Kapazität, 20 Kunden": "20 Kunden, Depot in der Mitte, 5 Ladungen, 0 % Reserve, f = 100: die Zelle mit dem größten ΔV (0,96); in 24 von 25 Instanzen sinkt die Fahrzeugzahl, die Lösung bei f = 400 ist dort im Mittel 10,6 % länger.",
    "Grenzfall: 2 % Reserve": "20 Kunden, Depot in der Mitte, 3 Ladungen, 2 % Reserve: ein Grenzfall (ΔV 0,16); nur in 4 von 25 Instanzen sinkt die Fahrzeugzahl bis f = 400; die gezeigte Instanz ist eine davon, mit kleinem Kipppunkt.",
    "Genug Reserve": "40 Kunden, Depot am Rand, 5 Ladungen, 10 % Reserve: in keiner der 25 Instanzen sinkt die Fahrzeugzahl bis f = 400.",
    "Wenige Ladungen": "Wie der Standard, aber 3 statt 5 Ladungen: ΔV 0,56, der rechnerische Kipppunkt liegt im Median bei f* = 13,4 (Standard: 28,9).",
}
