# Preset-Zufalls-Seeds

Die Zufalls-Seeds der Presets liegen ab 500000 (Messreihen: 1000 bis 1011 für die Formel, 2000 bis 2007 für das Orakel, 300000 bis 300024 für das Hauptraster, 310000 bis 310007 für die Mengenverteilungen). Geprüft mit `python tools/find_preset_seeds.py`: auf dem Lauf mit diesem Zufalls-Seed und 400 Iterationen zeigt jedes Preset seine Geschichte (Kriterien in `fgr_stories.py`, Tests in `tests/test_presets.py`). Suche: `--suche` probiert für ein Preset, dessen Seed die Geschichte nicht zeigt, die Seeds 500000 bis 500059 der Reihe nach.

| Preset | Zelle | Zufalls-Seed | Lauf: Fahrzeuge bei f = 0 / gewählt / f = 400 | Lauf: Distanz bei f = 0 / gewählt / f = 400 | Kipppunkt der Instanz |
|---|---|---|---|---|---|
| Standard | 40 Kunden, Mitte, 5 Ladungen, 0 % Reserve (Zelle 26) | 500000 | 6 / 5 / 5 | 712,3 / 743,9 / 743,9 | 31,6 |
| Knappe Kapazität, 20 Kunden | 20 Kunden, Mitte, 5 Ladungen, 0 % Reserve (Zelle 6) | 500011 | 6 / 6 / 5 | 644,3 / 644,3 / 752,3 | 108,0 |
| Grenzfall: 2 % Reserve | 20 Kunden, Mitte, 3 Ladungen, 2 % Reserve (Zelle 3) | 500011 | 4 / 3 / 3 | 511,0 / 511,5 / 511,5 | 0,5 |
| Genug Reserve | 40 Kunden, Rand, 5 Ladungen, 10 % Reserve (Zelle 39) | 500011 | 5 / 5 / 5 | 930,1 / 930,1 / 930,1 | keiner |
| Wenige Ladungen | 40 Kunden, Mitte, 3 Ladungen, 0 % Reserve (Zelle 22) | 500008 | 4 / 3 / 3 | 605,6 / 612,3 / 612,3 | 6,7 |

Distanzen in Längeneinheiten, Kipppunkt in Längeneinheiten je Fahrzeug. Ein Lauf ist eine Instanz: er streut um das Zellmittel (die Zellen in `data/fgr_results.json`), und die Meldungen der App stützen sich auf das Zellmittel. Die Läufe sind mit Windows (Python 3.14) gemessen; die Linux-Simulation (Docker, Python 3.12) prüft dieselben Geschichten in `tests/test_presets.py`.
