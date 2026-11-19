# Fahrzeuge oder Kilometer? Welche Fahrzeuggröße? – Streamlit-Demo

Fall-Demo für die Website „Sebastian Hanisch – Operations Research und Machine Learning“ (`demos.html`, Gruppe „Transport & Tourenplanung“). Ein Fahrzeug kostet **Fixkosten**, jeder Kilometer kostet auch: mehr Fahrzeuge heißen kürzere Wege, weniger Fahrzeuge längere (**CVRP mit Fixkosten je Fahrzeug**). Die Demo rechnet live auf **einer Instanz** drei Lösungen mit einer eigenen Suche, die kürzeste (Fixkosten 0), die kostenoptimale bei dem gewählten Wert und die bei den höchsten gemessenen Fixkosten (f = 400; meist die mit den wenigsten gefundenen Fahrzeugen), und stellt zwei Regler in den Mittelpunkt: die **Kapazitätsreserve** und die **Fixkosten**. OR-Tools mit Fixkosten und eine Kontinuumsformel für die Distanz laufen auf Knopfdruck. Die Aussagen stützen sich auf eine **vorgerechnete Messreihe** (40 Zellen, je 25 Instanzen, sieben Fixkostenstufen, Zufalls-Seeds ab 300000).

## Warum dieses Problem

Die naheliegende Frage der Flottenplanung lautet: Wann zwingt mich der Preis eines Fahrzeugs zu längeren Wegen? Die Rückladungs-Demo (`rueckladung-demo`) hat ausdrücklich ohne Fixkosten gemessen und nennt sie als offene Erweiterung; diese Demo ist das Anschlussstück. Der Aufhänger folgt der Messung und nicht einem gewünschten „es kippt bei X“: **Der Zielkonflikt „weniger Fahrzeuge oder weniger Kilometer“ besteht in den gemessenen Zufallsinstanzen (Mengen 5 bis 25) fast nur bei knapper Kapazität.** Wo die Kapazität Luft lässt, braucht die kürzeste Lösung kaum Fahrzeuge mehr als nötig: ab 5 % Reserve sinkt die Fahrzeugzahl bis f = 400 in nur 9 von 400 Instanzen. Dazu eine zweite Frage: Welche Distanz sagt eine Formel mit zwei angepassten Zahlen voraus?

## Modell

Ein Depot (am Rand (50, 0) oder in der Mitte (50, 50)), `n` Kunden (20 oder 40) gleichverteilt im 100 × 100-Gebiet, Mengen gleichverteilt ganzzahlig 5 bis 25, euklidische Entfernungen auf 0,1 Längeneinheiten gerundet. Unbegrenzt viele gleiche Fahrzeuge mit Kapazität `Q = max(⌈(1 + Reserve) · Σd / k⌉, größte Einzelmenge)`: `k` (3 oder 5) ist die Zahl der Ladungen, die Mindestzahl Fahrzeuge ist also etwa `k`; die Reserve (0, 2, 5 oder 10 %) ist der Laderaum über der Mindestmenge. Jedes genutzte Fahrzeug kostet `f` Längeneinheiten (0, 10, 25, 50, 100, 200 oder 400), jede gefahrene Längeneinheit kostet 1; Ziel sind die **Gesamtkosten `f · V + D`** (`V` Fahrzeuge, `D` Gesamtdistanz). Formeln im 📐-Expander der App.

Zu jedem `f` gehört die beste gefundene Lösung mit `V(f)` und `D(f)`. Der **rechnerische Kipppunkt** zweier Lösungen mit `V₀ > V₁` ist `f* = (D₁ − D₀) / (V₀ − V₁)`; die Befunde nennen ihn aus den Lösungen bei f = 0 und f = 400 (nicht unter 0) und zusätzlich die **erste Fixkostenstufe, bei der die Fahrzeugzahl unter die bei f = 0 sinkt** (eine Obergrenze des Kipppunkts auf dem Raster 10, 25, 50, 100, 200, 400). Eine **Zelle** ist eine Kombination aus Kundenzahl, Depot, Ladungen und Reserve (32 Zellen mit 3 oder 5 Ladungen; dazu 8 Zellen mit 2 oder 8 Ladungen bei 10 % Reserve; zusammen mit den 8 Zellen mit 3 oder 5 Ladungen bei 10 % Reserve bilden sie die 16 Formelzellen. Die 8 zusätzlichen Zellen zählen auch bei OR-Tools, bei der Fahrzeugzahl-Stufe und bei der Größenwahl); sie heißt **Zielkonflikt**, wenn das Zellmittel `ΔV = V(f = 0) − V(f = 400)` mindestens 0,3 beträgt, **kein Zielkonflikt**, wenn es unter 0,1 liegt, sonst **Grenzfall**. Die Grenzen 0,1 und 0,3 sind gesetzt, nicht hergeleitet. Die Fahrzeugzahl sinkt in der Messreihe nie um mehr als eins; ΔV ist zugleich der Anteil der Instanzen, in denen die Fahrzeugzahl sinkt (bei 25 Instanzen je Zelle: 0,3 heißt 8, die Grenze 0,1 heißt 2 Instanzen; einzelne Instanzen kippen so eine Zelle in die Nachbarklasse).

## Methodik

- **Eigene Suche** (Ruin-and-Recreate mit Relocate, Swap, 2-opt, 2-opt\*, Verschmelzen zweier Touren; Annahme nach Record-to-Record 0,4 %): die Fixkosten stehen im Einfügepreis. Start: Clarke-Wright; wenn Clarke-Wright mehr Fahrzeuge braucht als die untere Schranke `⌈Σd / Q⌉`, zusätzlich ein **Packungsstart** (eine Tiefensuche, die die Mengen auf `⌈Σd / Q⌉` Behälter verteilt; feste Knotengrenze, nur Ganzzahlen). Die Messreihe rechnet je Instanz alle sieben Fixkostenstufen in **zwei Durchgängen** (aufsteigend und absteigend in `f`, Warmstarts aus allen bisherigen Lösungen; für jedes `f` zählt die billigste aller gefundenen Lösungen, auch der anderen `f`; die „kürzeste Lösung“ kann also bei einem höheren `f` gefunden worden sein) mit 400 Iterationen je Suche. Die App rechnet live eine Kette mit den Stufen 0, dem gewählten `f` und 400 in **einem** Durchgang mit 100 oder 400 Iterationen (auch dort zählt je `f` die billigste aller gefundenen Lösungen).
- **Exaktes Verfahren** (Held-Karp je Kundenmenge plus Partitions-DP) bis 12 Kunden, nur für die Prüfung der Suche; für 20 und 40 Kunden gibt es mit Fixkosten kein exaktes Verfahren in der Demo.
- **OR-Tools** (Routing, Guided Local Search, `SetFixedCostOfAllVehicles`) in zwei Einstellungen: Standard (Erststrategie PATH_CHEAPEST_ARC) und SAVINGS; je Einstellung ein Lauf mit 3 s (20 Kunden) bzw. 6 s (40 Kunden) je Fixkostenstufe, höchstens ⌈Σd / Q⌉ + 4 Fahrzeuge.
- **Formel:** `D(Q) ≈ a · 2 · r̄ · Σd / Q + b · √(n · A)` (Struktur einer Kontinuumsnäherung nach Daganzo, über die Übersichtsarbeit arXiv 1706.05448 gelesen; Konstanten und Gültigkeitsbedingungen der Literatur nicht nachgeprüft; `a` und `b` angepasst, nicht übernommen) mit `r̄` = mittlerer Abstand Kunde–Depot und `A` = Gebietsfläche; relative kleinste Quadrate (Gewicht 1 / D²) auf 192 Lösungen mit eigenen Zufalls-Seeds (1000 bis 1011).
- **Größenwahl** (Nachmessung): vier Größen `k` = 2, 3, 5, 8 bei 10 % Reserve; Kostenfamilie: Fixkosten **und** Kilometerkosten je Fahrzeug wachsen mit `q^σ`, `q = Q / Q_ref` (`Q_ref` = `Q` bei `k` = 2, `f` ist der Wert dieser Größe); `σ < 1` ist Größenvorteil, `σ > 1` Größennachteil. Verglichen wird die beste Größe aus den gelösten Instanzen mit der, die die Formel wählt (Fahrzeugzahl `⌈Σd / Q⌉`, Distanz aus der Formel); „innere Stufe“ heißt `k` = 3 oder 5.
- **Messreihe:** `tools/messreihe.py` rechnet die Rohdaten (Stunden, nicht im Repo), `tools/dump_results.py` verdichtet sie zu `data/fgr_results.json` (unter 150 kB), aus dem App und Tests alle Zahlen lesen.

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen stehen in `data/fgr_results.json` (Aggregate der Messreihe, 1 000 Instanzzeilen in 40 Zellen, Zufalls-Seeds 300000 bis 300024) und werden in `tests/test_claims.py` nachgerechnet; die Spalte „Test“ nennt den Test.

| Frage | Befund | Test |
|---|---|---|
| Wann gibt es einen Zielkonflikt? | Von den 32 Zellen mit 3 oder 5 Ladungen sind 9 Zielkonflikt, 19 kein Zielkonflikt und 4 Grenzfälle; Zielkonflikt-Zellen bei 0 % Reserve 7 von 8 Zellen, bei 2 % 2 von 8, bei 5 % 0 von 8 und bei 10 % 0 von 8 | `test_claim_a_zielkonflikt_zellen_je_reserve` |
| Hängt das an der Reserve oder an anderen Faktoren? | Anteil der Zielkonflikt-Zellen nach Reserve 88 / 25 / 0 / 0 % (mittleres ΔV 0,64 / 0,24 / 0,03 / 0,01), nach Ladungen 19 % (3) und 38 % (5) (ΔV 0,16 und 0,30), nach Kunden 38 % (20) und 19 % (40) (ΔV 0,32 und 0,15), nach Depot 25 % (Rand) und 31 % (Mitte). Die Reserve ist der stärkste der vier Faktoren; den gesetzten Maßstab „mindestens 60 % auf einer und höchstens 20 % auf einer anderen Stufe“ erfüllt nur sie, Ladungen und Kundenzahl verdoppeln bzw. halbieren den Anteil. Die Reserve hat vier, die anderen Faktoren haben zwei Stufen; Maßstab und Reserve als Hauptfaktor wurden nach der Erkundung gesetzt (siehe „Ehrliche Grenzen“) | `test_claim_b_reserve_ist_der_staerkste_faktor` |
| Wie oft sinkt die Fahrzeugzahl? | Instanzen mit weniger Fahrzeugen bei f = 400 als bei f = 0 (je 100 Instanzen, 3 / 5 Ladungen): bei 0 % Reserve 55 / 73 %, bei 2 % 7 / 41 %, bei 5 % 1 / 6 %, bei 10 % 0 / 2 %; ab 5 % Reserve sinkt die Fahrzeugzahl bis f = 400 in nur 9 von 400 Instanzen | `test_claim_c_instanzen_mit_weniger_fahrzeugen` |
| Woher kommt es (Deutung)? | Die kürzeste Lösung nutzt im Mittel 0,69 / 0,24 / 0,04 / 0,01 Fahrzeuge mehr als die untere Schranke ⌈Σd / Q⌉ (Reserve 0 / 2 / 5 / 10 %, je 200 Instanzen); dass das am Packen liegt, ist eine Deutung aus dieser Zählung, nicht gesondert gemessen | `test_claim_e_ueberschuss_ueber_der_unteren_schranke` |
| Was kostet das Fahrzeug weniger? | Rechnerischer Kipppunkt f* = (D₄₀₀ − D₀) / (V₀ − V₄₀₀) (Instanzen mit weniger Fahrzeugen) bei 0 % Reserve Median 26,1 (Quartile 12,4, 26,1, 47,5; Interpolation zwischen Instanzwerten) (128 Instanzen), bei 2 % Median 10,4 (Quartile 4,1, 10,4, 19,6; Interpolation zwischen Instanzwerten) (48 Instanzen); erste Fixkostenstufe mit weniger Fahrzeugen bei 0 % Reserve in 26 / 36 / 34 / 24 / 6 / 2 Instanzen (Stufen 10 / 25 / 50 / 100 / 200 / 400); Distanz der Lösung bei f = 400 gegen die bei f = 0 in den Instanzen mit weniger Fahrzeugen im Mittel 5,5 % (128 Instanzen), 2,4 % (48 Instanzen), 2,0 % (7 Instanzen), 1,0 % (2 Instanzen) (Reserve 0 / 2 / 5 / 10 %) | `test_claim_d_kipppunkt_und_preis` |
| Ist die Lösung bei f = 400 die mit den wenigsten Fahrzeugen? | Sie hat in 990 von 1000 Instanzen die untere Schranke ⌈Σd / Q⌉ an Fahrzeugen; die übrigen 10 liegen alle bei 0 % Reserve, ob die Schranke dort unerreichbar ist oder die Suche sie verfehlt, ist nicht unterschieden. In 3 Instanzen mit weniger Fahrzeugen ist die Distanz bei f = 400 nicht länger als bei f = 0 (dort f* = 0); ΔV ist zugleich der Anteil der Instanzen, in denen die Fahrzeugzahl sinkt | `test_claim_s_untere_schranke_gleiche_distanz_und_dv_gleich_anteil` |
| Kurve oder Stufe? | In keiner der 1 000 Instanzzeilen kommen mehr als zwei verschiedene Fahrzeugzahlen vor: die Front ist eine Stufe, keine Kurve (für diese Instanzen, mit sieben Fixkostenstufen und Kapazitäten nahe `Σd / k`) | `test_claim_f_front_ist_eine_stufe` |
| Größte Front | größtes ΔV: Zelle 6 (20 Kunden, Depot Mitte, 5 Ladungen, 0 % Reserve) mit 0,96 | `test_claim_g_groesste_und_kleinste_zelle` |
| Welche Distanz sagt die Formel voraus? | a = 0,939, b = 0,627 (angepasst an 192 Lösungen); mittlerer Fehler auf den Anpassungsdaten 4,0 % (größter 18,8 %); auf den Messläufen 14 von 16 Zellen höchstens 5 %, Spanne 1,8 bis 5,3 %, Mittel über die Zellen 3,7 %; keine Zelle erreicht 10 %; je Instanz im Mittel 3,7 % (größter 16,4 %), 20 von 400 Instanzen ab 10 %; Zell-Bias zwischen -5,0 und +3,2 %. Getestet in denselben 16 Zellen wie angepasst (andere Zufalls-Seeds), gegen die Lösung der eigenen Suche, nicht gegen das Optimum | `test_claim_h_formel` |
| Welche Fahrzeuggröße wählt die Formel? | Kostenfamilie: Fixkosten und Kilometerkosten je Fahrzeug wachsen mit q^σ (q = Q / Q_ref, Q_ref = Q bei k = 2), σ < 1 ist Größenvorteil, σ > 1 Größennachteil; vier Größen k = 2, 3, 5, 8 bei 10 % Reserve; „innere Stufe“ heißt k = 3 oder 5. Für σ = 1, 1,5 und 2 ist das kleinste Fahrzeug (k = 8) bei allen vier Fixkostenstufen (25, 50, 100, 200) in allen 100 Fällen je Zeile das billigste, bei Messung und Formel (kein Aussagewert für die Formel); ein inneres Optimum gibt es nur bei kleinem σ und kleinem f: σ = 0,5, f = 25: 82 von 100 Fällen mit innerer Stufe als bester, Formel trifft dieselbe Stufe in 73 von 100 (62 von 82 bei innerer Stufe), die beste konstante Wahl in 57 von 100; σ = 0,5, f = 100: 30 von 100, Formel trifft 71 von 100 (1 von 30 bei innerer Stufe), die beste konstante Wahl (k = 2) 70 von 100; σ = 0,4, f = 25: 53 von 100, 64 von 100 (19 von 53), konstant 49 von 100; bei f = 200 ist für σ = 0,4 und 0,5 in keinem Fall eine innere Stufe die beste; kleinere σ als 0,4 sind nicht gemessen | `test_claim_i_groessenwahl` |
| Wie schlägt sich OR-Tools? | 1600 Läufe (darunter die 8 Zellen mit k = 2 und 8): OR-Tools bekam je Fixkostenstufe 3 s (20 Kunden) bzw. 6 s (40 Kunden) je Einstellung, die Zahl „bessere der beiden Einstellungen“ also das Doppelte; die eigene Kette brauchte im Mittel 1,7 s bzw. 3,3 s je Fixkostenstufe (zwei Suchen, unter Last mit sechs parallelen Prozessen gemessen) und nimmt je f die billigste aus allen ihren Läufen. Je Lauf die bessere der beiden Einstellungen im Mittel +0,49 % gegen die eigene Suche (OR-Tools besser in 13 von 800 Läufen, größte Abweichung +21,2 %), aber in 482 von 800 Läufen gleich (Median 0,0 %, 131 Läufe über 1 %, 10 über 5 %). Gleiche Rechenzeit wurde nicht gemessen; keine Obergrenze und keine Rangfolge der Löser; OR-Tools durfte höchstens ⌈Σd / Q⌉ + 4 Fahrzeuge nutzen | `test_claim_j_ortools` |
| Wie nah ist die eigene Suche am Optimum? | 12 Kunden, k = 3, Reserve 0, 2 und 10 % (5 % nicht gerechnet), 16 Instanzen × 7 Fixkostenstufen = 112 Fälle je Reserve, nicht unabhängig (Zufalls-Seeds 2000 bis 2007, 2 Depots): mittlere Kostenlücke bei Reserve 0 % 0,040 % (3 von 112 Fällen über 0,5 %, größte 2,02 %, die Fälle über 0,5 % aus 1 Instanz), bei 2 % 0,000 %, bei 10 % 0,000 %; ein Durchgang über die sieben Stufen 0,147 % (14 Fälle über 0,5 % aus 4 Instanzen); Live-Kette der App (f = 0, 100, 400) über 48 Fälle 0,112 %, die Kette der Messreihe auf denselben 48 Fällen 0,062 %. Das Orakel misst die Kostenlücke, nicht die Höhe des Zielkonflikts | `test_claim_k_orakel_bei_12_kunden` |
| Gilt das für andere Mengen? | Zielkonflikt-Zellen je Reserve 0 / 2 / 5 / 10 % (je 8 Zellen, 8 Instanzen, Zufalls-Seeds 310000 bis 310007): gleich 5 bis 25: 7 / 2 / 0 / 0; weit 1 bis 40: 7 / 2 / 1 / 0; schief: 5 / 0 / 0 / 0; fast gleich 14 bis 16: 5 / 3 / 0 / 0; bei „weit 1 bis 40“ bleibt bei 5 % Reserve eine Zelle (von 8) mit Zielkonflikt (3 von 8 Instanzen mit weniger Fahrzeugen); bei „fast gleich 14 bis 16“ liegen die Zielkonflikt-Zellen bei 2 % Reserve (3 von 8) über der Kontrolle „gleich 5 bis 25“ (2 von 8); bei „schief“ bindet die größte Menge die Kapazität in 6 / 6 / 4 / 2 von 64 Instanzen (Reserve 0 / 2 / 5 / 10 %) | `test_claim_l_andere_mengenverteilungen` |
| Was ist anders als in der Vormessung? | siehe „Befunde und Korrekturen“ | `test_claim_m_abweichungen_zur_vormessung` |

## Befunde und Korrekturen

Die Demo hat die Vormessung (`messreihe_flotte/`, 2026-11-18) mit einem geänderten Packungsstart komplett neu gerechnet. Die Vormessung nutzte einen CP-SAT-Lauf; er fand in der einen abweichenden Zeile (die Diagnose lief nur dort) auf Windows und Linux verschiedene Packungen (Restmessung AP 0: 11 von 12 Zeilen gleich); die Demo nimmt eine deterministische Tiefensuche. Die neue Suche wurde auf diesen zwölf Zeilen nicht erneut zwischen Windows und Linux verglichen; belegt ist nur der Docker-Lauf der Tests. Vergleich der neu gerechneten Zahlen mit denen der Vormessung (Auswahl, nicht vollständig; die Verschiebungen sind klein, die Aussagen bleiben, der Packungsstart ist die naheliegende, aber nicht isolierte Ursache):

- Zielkonflikt / kein Zielkonflikt / Grenzfall 9 / 19 / 4 (Vormessung 9 / 19 / 4).
- Zielkonflikt-Zellen je Reserve 7 / 2 / 0 / 0 (Vormessung 7 / 2 / 0 / 0).
- Instanzen mit weniger Fahrzeugen je Reserve 128 / 48 / 7 / 2 (Vormessung 129 / 46 / 7 / 2).
- größtes ΔV 0,96 (Vormessung 0,92).
- Formel: a = 0,939 und b = 0,627 (Vormessung 0,939 und 0,627).
- Vormessung zur Lücke der Suche bei 12 Kunden (ein Durchgang über die sieben Stufen, CP-SAT-Packungsstart; nicht neu gerechnet): mittlere Lücke 0,267 % (15 von 112 Fällen über 0,5 %, größte 6,85 %); mit dem Verfahren der Demo (ein Durchgang über die sieben Stufen, deterministischer Packungsstart; zusätzlich zählt je f die billigste aller gefundenen Lösungen) 0,147 % (14 von 112 über 0,5 %, größte 2,02 %); der Unterschied ist nicht auf eine einzelne Ursache zurückgeführt.
- Nicht neu gerechnet (in der App als Vormessung gekennzeichnet, mit dem früheren Packungsstart gemessen): 400 gegen 1 500 Iterationen auf drei Bedingungen (mittlere Mehrkosten 0,22 %, größte 2,66 %, 36 Läufe) und die Kontrolle auf 16 Zellen mit 1 500 Iterationen (Fahrzeugzahl in 4 von 336 Werten verschieden, Zielkonflikt-Zellen 11 gegen 11).
- OR-Tools wurde neu gerechnet (zeitbegrenzt, nicht deterministisch): schon die neuen OR-Tools-Läufe gegen die alte eigene Suche liegen bei +0,51 % (besser in 11 von 800), in der Vormessung waren es +0,61 % (besser in 11 von 800), jetzt gegen die neue eigene Suche +0,49 % (besser in 13 von 800); der Wechsel der Zahl kommt also größtenteils vom Neulauf, und 11 gegen 13 von 800 liegt im Rauschen.

## Ehrliche Grenzen

- **Die Höhe der Front bei Reserve 0 % ist die der Suche.** Die eigene Suche ist kein Optimum; das exakte Verfahren gibt es nur bis 12 Kunden (k = 3, Reserve 5 % nicht gerechnet), und dort misst es die Kostenlücke, nicht die Höhe des Zielkonflikts: bei Reserve 0 % im Mittel 0,040 % (3 von 112 Fällen über 0,5 %, alle aus einer Instanz bei hohen Fixkosten). Ob die Suche bei 20 und 40 Kunden die Front ebenso trifft, ist nicht gemessen. „Kein Zielkonflikt ab 5 % Reserve“ ist robuster als die Höhe darunter.
- **Zufallsinstanzen mit gleichverteilten Mengen 5 bis 25:** „knappe Kapazität“ heißt hier Packen nahe an 100 % Auslastung. In drei anderen Mengenverteilungen (Tab „Messreihe“) fällt der Zielkonflikt bei 0 % Reserve unterschiedlich hoch aus, bei „weit 1 bis 40“ bleibt eine Zelle bei 5 % Reserve ein Zielkonflikt; Praxisdaten sind nicht gemessen.
- **Reserve als Hauptfaktor, Schwellen nach einer Erkundung:** auf anderen Zufalls-Seeds (100000 bis 100004, n = 20 und 40, Depot Rand, 150 Iterationen) fiel auf, dass sich die Fahrzeugzahl mit f bei Reserve 10 % fast nie, bei 0 % häufig ändert; danach wurden die Reserve zum Hauptfaktor des Rasters und die Schwellen (0,1 und 0,3 für ΔV, 60 und 20 % für „trennt“) gesetzt. Die Messreihe selbst kam danach.
- **Die Formel ist angepasst, nicht übernommen.** Konstanten und Gültigkeitsbedingungen der Literatur sind nicht nachgeprüft: in der Übersichtsarbeit arXiv 1706.05448 ließ sich die Struktur, aber kein Zahlenwert der Konstanten und keine Gültigkeitsbedingung finden. Getestet ist die Formel nur in den 16 Zellen (20 und 40 Kunden, 10 % Reserve, f = 0), an denen auch angepasst wurde, gegen die Lösung der eigenen Suche.
- **Größenwahl:** für σ ≥ 1 ist in allen gemessenen Fällen das kleinste Fahrzeug das billigste (Tabelle oben), die Kennzahl „Formel trifft die beste Größe“ hat dort keinen Aussagewert; eine innere Stufe als beste gab es nur bei σ = 0,4 und 0,5 und nicht bei f = 200, und bei f = 100 trifft die Formel sie selten (fast immer wählt sie dort k = 2, die häufigste beste Größe).
- **OR-Tools** liegt im Mittel über der eigenen Suche, aber in 482 von 800 Läufen gleich; die Zeitlimits (3 s bzw. 6 s je Einstellung) und die der eigenen Kette sind nicht angeglichen (siehe Tabelle oben). Das ist keine Obergrenze des Rückstands und keine Rangfolge der Löser.
- **Literatur** nur als Zusammenfassungen gelesen (Daganzo 1984, Transportation Research B 18; Golden, Assad, Levy, Gheysens 1984, Computers & Operations Research 11); kein Literaturvergleich.
- **Rechenzeit** (Messung dieser README, nicht im Test; Windows, ein Prozess, Python 3.14, 16 logische Prozessoren, Mittel über drei Instanzen mit den Zufalls-Seeds 500000 bis 500002, Depot Mitte, 5 Ladungen, Reserve 0 %, f = 50): die Live-Kette (drei Stufen, ein Durchgang) braucht bei 20 Kunden 0,4 s mit 100 und 2,0 s mit 400 Iterationen, bei 40 Kunden 1,6 s und 6,1 s. Auf Streamlit Cloud ist die Zeit nicht gemessen.
- **Warum ein Packungsstart nötig ist** (Befund der Vorbereitung der Vormessung mit dem früheren Packungsstart, nicht neu gemessen): die Suche allein fand bei knapper Kapazität die Fahrzeugzahl bei mittlerem f nicht stabil.

## Verifikation

- **Kern:** eigene Suche gegen eine Vollaufzählung (n ≤ 7, alle Reihenfolgen mit Split-DP) und ein CP-SAT-Modell (n = 9) über das exakte Verfahren, Held-Karp mit Partitions-DP (`tests/test_oracle_fahrzeuggroesse.py`); die Suche liegt nie unter dem Optimum. Handbeispiele von Hand, Prüfer erkennt Überlast, doppelte und fehlende Kunden, Randfälle (ein und zwei Kunden, Kapazität gleich der größten Menge).
- **Packungsstart:** deterministisch, Ganzzahlen, keine Zeit; Handbeispiele und Unmöglichkeit (`tests/test_search.py`).
- **Zweig:** bei Reserve 0 % sinkt die Fahrzeugzahl auf mindestens einer Instanz von f = 0 auf f = 400 (Nullspalten-Falle).
- **Ergebnisdatei:** innere Widerspruchsfreiheit je Zelle, je Reserve und je Faktor (`tests/test_results.py`); jede Zahl der README in `tests/test_claims.py`.
- **Presets:** Zelle und Geschichte jedes Presets gegen die Ergebnisdatei und den Lauf (`tests/test_presets.py`, `tools/PRESET_SWEEP.md`).
- **Verdikte:** reine Funktionen, an Schwellen und handgesetzten Werten (`tests/test_verdicts.py`); Layout, Presets, AppTest und PDF.
- **Plattform:** Neu-Rechnen als Band (`tests/test_reproduktion.py`); Linux-CI-Simulation mit Docker vor dem Push.
- **Umfang:** 176 Tests.

## Dateistruktur

| Datei | Zweck |
|---|---|
| `.github/workflows/tests.yml` | CI: Push, Pull Request, wöchentlicher Canary |
| `.gitignore` | venv, Caches, Streamlit-Secrets |
| `.streamlit/config.toml` | Streamlit-Einstellungen (keine Nutzungsstatistik) |
| `app.py` | Streamlit-App (Skelett nach DEMO-PLAYBOOK §2) |
| `fgr_constants.py` | Regler-Stufen, feste Annahmen, Schwellen, Farben, Presets |
| `fgr_model.py` | Instanz, Kapazität, Kosten, Prüfer, Clarke-Wright |
| `fgr_search.py` | eigene Suche, deterministischer Packungsstart, Ketten |
| `fgr_solvers.py` | OR-Tools mit Fixkosten, exaktes Verfahren bis 12 Kunden |
| `fgr_formula.py` | Kontinuumsformel, Anpassung von a und b |
| `fgr_rng.py` | SplitMix64 (nur Ganzzahlen, plattformfest) |
| `fgr_results.py` | Laden und Auswerten von `data/fgr_results.json` |
| `fgr_evaluation.py` | Live-Analyse, Kennzahlen, Verdikte als reine Funktionen |
| `fgr_stories.py` | Abnahmekriterien der Presets |
| `fgr_visualization.py` | Plotly-Abbildungen (Achsen gesperrt) |
| `fgr_pdf_export.py` | Tourenplan als PDF (fpdf2) |
| `fgr_layout.py` | fester Kopf (Stylesheet) |
| `fgr_presets.py` | Permalink (Begrenzen, Einrasten), Presets (Schnellstart in der Seitenleiste, aktives Preset hervorgehoben), Zufalls-Seed-Button |
| `data/fgr_results.json` | Aggregate der Messreihe |
| `tools/messreihe.py` | Messreihen (Stunden; Rohdaten nicht im Repo) |
| `tools/dump_results.py` | verdichtet die Rohdaten zu `data/fgr_results.json` |
| `tools/find_preset_seeds.py`, `tools/PRESET_SWEEP.md` | Zufalls-Seeds der Presets |
| `requirements-dev.txt` | Laufzeit plus pytest und NumPy |
| `requirements.txt` | Laufzeit-Bibliotheken (ungepinnt) |
| `tests/` | Mini-Instanz von Hand, Orakel, Suche, Ergebnisdatei, Claims, Presets, Verdikte, Layout, AppTest, PDF, Footer, Laufzeit-Importe |

## Bewusst nicht umgesetzt

- **Flottenmix** (zwei oder mehr Fahrzeuggrößen gleichzeitig): in der Vormessung gemessen, aber nicht belegt: die Suche hat keine Züge, die gezielt gemischte Flotten bilden; bei 12 Kunden (Vormessung, nicht neu gerechnet; nur σ = 1, Kapazitätspaar k = 8 und 3, f = 100, 24 Instanzen) liegt der exakte Mix im Mittel 0,24 % unter der besten der vier Einheitsflotten (1,75 % unter der besseren der beiden des Paares), bei 20 und 40 Kunden ist der Vorteil unbekannt. Ob ein besserer Mix-Löser lohnt, ist eine offene Frage, keine Zusage.
- **Begrenzte Fahrzeugzahl, Zeitfenster, Servicezeiten, Praxisinstanzen** und mehr als 40 Kunden.
- **Mengenverteilung als Regler:** die vier Verteilungen stehen nur als Messreihe in der App (Tab „📈 Messreihe“), nicht als Regler; die Grenze „kein Zielkonflikt ab 5 % Reserve“ verlangte keinen.
- **Rückladungen:** `rueckladung-demo` (Leerfahrten, ausdrücklich ohne Fixkosten gemessen).
- **Kopplung mit Lagerhaltung:** `inventory-routing-demo` (anderes Modell).

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Die Messreihe selbst (Stunden Rechenzeit, nicht Teil der Tests) läuft mit `python tools/messreihe.py <art>` (Arten m1, fit, ort, orakel, mengen) und wird mit `python tools/dump_results.py` zu `data/fgr_results.json` verdichtet; `python tools/find_preset_seeds.py` prüft die Zufalls-Seeds der Presets.

Gebaut mit Streamlit, Plotly, pandas, OR-Tools und fpdf2.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zum Thema: [Tourenplanung optimieren](https://sebastianhanisch.net/tourenplanung-optimierung.html).
