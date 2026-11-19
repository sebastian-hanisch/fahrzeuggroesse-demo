"""PDF-Export: Sonderzeichen werden bereinigt, jede Lösung lässt sich als PDF ausgeben."""

import pytest

import fgr_evaluation as E
import fgr_pdf_export as PDF

SETTINGS = E.Settings(20, "mitte", 5, 0.0, 100, 100, 3)


def test_clean_ersetzt_sonderzeichen_und_streicht_emoji():
    text = PDF.clean("Fahrzeuge – Σd ≥ 20 % → ± 5 € „Test“ 🚚 ✓ Δ ⌈x⌉")
    assert "–" not in text and "→" not in text and "±" not in text and "€" not in text and "🚚" not in text and "Δ" not in text and "Σ" not in text
    assert "Fahrzeuge" in text and ">= 20" in text and "EUR" in text and "Summe" in text
    text.encode("latin-1")   # muss in der Standardschrift darstellbar sein


@pytest.fixture(scope="module")
def analyse():
    return E.analyse(SETTINGS)


@pytest.mark.parametrize("key", ["f0", "sel", "f400"])
def test_pdf_fuer_jede_loesung(analyse, key):
    data = PDF.build_pdf(SETTINGS, analyse, key)
    assert data[:5] == b"%PDF-" and len(data) > 1500
