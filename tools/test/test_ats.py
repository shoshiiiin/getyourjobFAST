"""Tests des ATS-Abgleichs. Ohne Netz, ohne Dateien."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ats import Abgleich, abgleichen, begriffe, bericht, kurzfassung, passt, steckt_drin  # noqa: E402

ANZEIGE = """Du leitest Projekte und modellierst Prozesse in BPMN.
- Mehrjährige Erfahrung in der Leitung von Projekten
- Sicher im Umgang mit SAP und Power Platform
Wir bieten 30 Urlaubstage."""


class BegriffeTest(unittest.TestCase):
    def test_findet_substantive_und_abkuerzungen(self):
        g = begriffe(ANZEIGE)
        self.assertIn("Prozesse", g)
        self.assertIn("BPMN", g)
        self.assertIn("SAP", g)

    def test_fuellwoerter_fallen_raus(self):
        g = begriffe(ANZEIGE)
        for wort in ("Wir", "und", "Urlaubstage", "Erfahrung"):
            self.assertNotIn(wort, g, wort)

    def test_zweiwortpaar_wird_erkannt(self):
        self.assertIn("Power Platform", begriffe(ANZEIGE))

    def test_kein_paar_ueber_satzgrenze(self):
        g = begriffe("Wir suchen Leitung. Projekte warten.")
        self.assertNotIn("Leitung Projekte", g)

    def test_kein_paar_ueber_komma(self):
        self.assertNotIn("Standorte Beschäftigte", begriffe("sechs Standorte, 300 Beschäftigte"))

    def test_bullets_zaehlen_doppelt(self):
        g = begriffe("- Prozesse aufnehmen")
        self.assertEqual(g["Prozesse"], 2)

    def test_kandidatenfilter_wirft_adjektive_am_satzanfang_weg(self):
        text = "Abgeschlossenes Studium erwartet."
        self.assertIn("Abgeschlossenes", begriffe(text))
        self.assertNotIn("Abgeschlossenes", begriffe(text, kandidaten=True))

    def test_kandidatenfilter_laesst_substantiv_am_bulletanfang_stehen(self):
        """Der Filter darf Unterlagen nicht köpfen — dort wird er nie benutzt."""
        self.assertIn("Leitung", begriffe("- Leitung der Einführung eines Systems"))


class PasstTest(unittest.TestCase):
    def test_beugungsformen_passen(self):
        self.assertTrue(passt("Prozesse", "Prozessen"))
        self.assertTrue(passt("Projekten", "Projekt"))

    def test_verschiedene_woerter_passen_nicht(self):
        self.assertFalse(passt("Projekt", "Projektion"))   # Längendifferenz zu klein? nein: Stamm reicht nicht
        self.assertFalse(passt("Abnahme", "Anfrage"))

    def test_kurze_woerter_nur_exakt(self):
        self.assertTrue(passt("SAP", "sap"))
        self.assertFalse(passt("SAP", "SAPV"))

    def test_steckt_drin(self):
        self.assertTrue(steckt_drin("Prozesse", {"Prozessen", "Anderes"}))
        self.assertFalse(steckt_drin("Prozesse", {"Anderes"}))


class AbgleichTest(unittest.TestCase):
    def test_drei_gruppen(self):
        a = abgleichen(
            anzeige="Wir brauchen BPMN, Rollout und SAP.",
            unterlagen="Ich habe BPMN modelliert.",
            belege="Rollout über sechs Standorte.",
        )
        self.assertIn("BPMN", [w for w, _ in a.drin])
        self.assertIn("Rollout", [w for w, _ in a.luecke])
        self.assertIn("SAP", [w for w, _ in a.ungedeckt])

    def test_abdeckung_rechnet(self):
        a = Abgleich(drin=[("a", 1)], luecke=[("b", 1)], ungedeckt=[("c", 1), ("d", 1)])
        self.assertEqual(a.geprueft, 4)
        self.assertAlmostEqual(a.abdeckung, 25.0)

    def test_leerer_abgleich_stuerzt_nicht_ab(self):
        a = abgleichen("", "", "")
        self.assertEqual(a.geprueft, 0)
        self.assertEqual(a.abdeckung, 0.0)

    def test_mindesthaeufigkeit_filtert(self):
        a = abgleichen("Einmalig kommt Datenschutz vor.", "", "", mindest=5)
        self.assertEqual(a.geprueft, 0)


class BerichtTest(unittest.TestCase):
    def test_bericht_nennt_alle_drei_gruppen(self):
        a = abgleichen("BPMN und Rollout.", "BPMN.", "Rollout.")
        text = bericht(a)
        self.assertIn("IN DEINEN UNTERLAGEN", text)
        self.assertIn("FEHLT, OBWOHL BELEGT", text)
        self.assertIn("FEHLT UND IST NICHT BELEGT", text)

    def test_kurzfassung_nennt_luecken(self):
        a = abgleichen("BPMN und Rollout.", "BPMN.", "Rollout.")
        self.assertIn("belegte Lücke", kurzfassung(a))

    def test_kurzfassung_ohne_luecken_schweigt_dazu(self):
        a = abgleichen("BPMN.", "BPMN.", "")
        self.assertNotIn("Lücke", kurzfassung(a))


if __name__ == "__main__":
    unittest.main()
