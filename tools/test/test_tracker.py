"""Tests für die reinen Teile von tools/tracker.py.  Aufruf: tools/.venv/bin/python -m unittest discover -s tools/test"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tracker import gleiche_firma, norm_firma, stelle_lesen  # noqa: E402

STELLE = """# Projektmanager (w/m/d)

**Muster GmbH** · Musterstadt 50667 · FULL_TIME

| | |
|---|---|
| Quelle | StepStone |
| URL | https://www.stepstone.de/x-14419799-inline.html |
"""


class NormFirmaTest(unittest.TestCase):
    def test_umlaute_und_sonderzeichen_werden_aufgeloest(self):
        self.assertEqual(norm_firma("Wirtschaftsförderung Frankfurt GmbH"), "wirtschaftsfoerderungfrankfurt")

    def test_leere_eingabe_ergibt_leeren_schluessel(self):
        self.assertEqual(norm_firma(None), "")


class GleicheFirmaTest(unittest.TestCase):
    def test_rechtsform_aendert_nichts(self):
        self.assertTrue(gleiche_firma("Meffert AG Farbwerke", "Meffert"))

    def test_kurze_schluessel_verwechseln_keine_firmen(self):
        self.assertFalse(gleiche_firma("DAW SE", "DAWI Consulting"))

    def test_rechtsform_auf_beiden_seiten(self):
        self.assertTrue(gleiche_firma("FRANK GmbH", "FRANK"))
        self.assertTrue(gleiche_firma("conet Deutschland GmbH", "conet"))

    def test_aehnliche_konzerne_bleiben_getrennt(self):
        self.assertFalse(gleiche_firma("Deutsche Bahn AG", "Deutsche Bank AG"))

    def test_zu_kurze_namen_gelten_nie_als_gleich(self):
        self.assertFalse(gleiche_firma("AB", "AB"))


class StelleLesenTest(unittest.TestCase):
    def test_liest_kopf_und_passung(self):
        with tempfile.TemporaryDirectory() as tmp:
            ordner = Path(tmp) / "2026-09-01-muster-projektmanager"
            ordner.mkdir()
            (ordner / "stelle.md").write_text(STELLE, encoding="utf-8")
            (ordner / "analyse.md").write_text("**Passung 92 von 100**", encoding="utf-8")

            daten = stelle_lesen(ordner)

        self.assertEqual(daten["firma"], "Muster GmbH")
        self.assertEqual(daten["rolle"], "Projektmanager (w/m/d)")
        self.assertEqual(daten["ort"], "Musterstadt")
        self.assertEqual(daten["quelle"], "StepStone")
        self.assertEqual(daten["passung"], 92)
        self.assertEqual(daten["unterlagen"], "stellen/2026-09-01-muster-projektmanager")

    def test_ohne_stelle_md_bleibt_nur_der_ordner(self):
        with tempfile.TemporaryDirectory() as tmp:
            ordner = Path(tmp) / "x"
            ordner.mkdir()
            self.assertEqual(stelle_lesen(ordner), {"unterlagen": "stellen/x"})


if __name__ == "__main__":
    unittest.main()
