"""Kontinuumsformel für die Distanz und die Fahrzeugzahl (Struktur nach Daganzo, Konstanten a und b hier angepasst, nicht übernommen).

  D(Q) ≈ a · 2 · r̄ · Σd / Q + b · √(n · A)

r̄ = mittlerer Abstand Kunde–Depot, Σd = Gesamtmenge, Q = Kapazität, n = Zahl der Kunden, A = Gebietsfläche (100 · 100 Längeneinheiten). Der erste Summand ist
die Strecke zwischen Depot und Gebiet (jede Ladung fährt hin und zurück), der zweite die Strecke im Gebiet (wächst mit √(n · A)). Die Fahrzeugzahl
folgt aus V(Q) = ⌈Σd / Q⌉. Alle Längen in Entfernungseinheiten (1 Einheit = 0,1 Längeneinheit)."""

import math

import fgr_model as M

AREA = (100.0 * M.SCALE) ** 2


def predicted_distance(inst, Q, a, b):
    """D̂(Q) in Entfernungseinheiten für die Orte und Mengen der Instanz (die Kapazität der Instanz wird nicht gelesen)."""
    return a * 2.0 * M.depot_dist_mean(inst) * sum(inst.dem) / Q + b * math.sqrt(inst.n * AREA)


def predicted_vehicles(inst, Q):
    return int(math.ceil(sum(inst.dem[1:]) / Q))


def fit_ab(rows):
    """Kleinste Quadrate für D = a · x1 + b · x2 über rows = [(D, x1, x2)], relativ gewichtet (Gewicht 1 / D², also relative kleinste Quadrate)."""
    s11 = s12 = s22 = t1 = t2 = 0.0
    for D, x1, x2 in rows:
        w = 1.0 / (D * D)
        s11 += w * x1 * x1
        s12 += w * x1 * x2
        s22 += w * x2 * x2
        t1 += w * D * x1
        t2 += w * D * x2
    det = s11 * s22 - s12 * s12
    return (t1 * s22 - t2 * s12) / det, (s11 * t2 - s12 * t1) / det


def size_cost(Q, Q_ref, sigma, f_int, vehicles, distance):
    """Gesamtkosten einer Fahrzeuggröße in der Kostenfamilie q^σ: Fixkosten und Kilometerkosten je Fahrzeug wachsen mit q = Q / Q_ref wie q^σ."""
    return (Q / Q_ref) ** sigma * (f_int * vehicles + distance)
