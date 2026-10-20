"""
Tests der Filtermechanik.

Wichtig: Diese Tests setzen ihr **eigenes** Mandat und ihren eigenen Wohnort.
Sie prüfen, dass die Mechanik stimmt — nicht, was gerade in profil/ steht.
Dadurch bleiben sie grün, egal wer das Repo benutzt.

These tests inject their own mandate and home location, so they test the
mechanics rather than whoever's profile currently sits in profil/.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from suche import filter as f  # noqa: E402
from suche.filter import (  # noqa: E402
    REMOTE_VOLL, einordnen, fach_bezug, km, orte, schluessel, signale, titel_art, titel_passt,
)

# Ein erfundenes Mandat: Datenschutz. Bewusst ein anderes Fach als das
# Beispielprofil, damit auffällt, falls doch aus profil/ gelesen wird.
TEST_MANDAT = {
    "titel_ausschluss": r"(werkstudent|praktik|trainee|teilzeit|part.?time)",
    "titel_kern": r"(datenschutz|privacy|dsgvo)",
    "titel_allgemein": r"(consultant|berater|manager|referent)",
    "fach_ausschluss": r"(audit|cyber|security|\bsps\b)",
    "kern_wort": r"(datenschutz|dsgvo|privacy|auftragsverarbeitung)",
}
KOELN = (50.9375, 6.9603)
BONN = (50.7339, 7.0998)
DUESSELDORF = (51.2254, 6.7763)


def setUpModule() -> None:
    f.setze_mandat(TEST_MANDAT)
    f.setze_heimat(KOELN, 30.0)


class TitelTest(unittest.TestCase):
    def test_zielrolle_passt(self):
        self.assertTrue(titel_passt("Datenschutzbeauftragter (m/w/d)"))
        self.assertTrue(titel_passt("Privacy Manager"))

    def test_ausgeschlossene_titel_fallen_raus(self):
        self.assertFalse(titel_passt("Werkstudent Datenschutz"))
        self.assertFalse(titel_passt("Datenschutz-Referent in Teilzeit"))

    def test_fremdes_fachgebiet_faellt_trotz_passendem_titel_raus(self):
        self.assertFalse(titel_passt("Consultant IT Audit"))
        self.assertFalse(titel_passt("Manager Cyber Security"))

    def test_allgemeine_rolle_braucht_fachbezug_im_text(self):
        self.assertEqual(titel_art("Senior Consultant (m/w/d)"), "allgemein")
        self.assertEqual(titel_art("Datenschutz-Berater:in"), "kern")
        job = {"titel_art": "allgemein", "km": 5, "beschreibung": "Beratung im Bauwesen"}
        self.assertEqual(einordnen(job), "raus")
        job["beschreibung"] = "Du betreust die DSGVO und den Datenschutz beim Kunden."
        self.assertEqual(einordnen(job), "lokal")

    def test_titel_ohne_zielbegriff_faellt_raus(self):
        self.assertFalse(titel_passt("Teamassistenz Einkauf"))
        self.assertFalse(titel_passt(""))


class SignalTest(unittest.TestCase):
    def test_findet_vollremote_einmal_je_wortlaut(self):
        text = "Du arbeitest 100% remote. Wirklich 100% remote, deutschlandweit."
        self.assertEqual(signale(text, REMOTE_VOLL), ["100% remote"])

    def test_hybrid_ist_kein_vollremote(self):
        self.assertEqual(signale("Hybrid, 2 Tage im Büro", REMOTE_VOLL), [])


class OrtTest(unittest.TestCase):
    def test_zerlegt_und_entfernt_rauschen(self):
        self.assertEqual(orte("Eschborn, Hessen, Deutschland"), ["Eschborn"])
        self.assertEqual(orte("Köln / Bonn"), ["Köln", "Bonn"])

    def test_bonn_liegt_im_umkreis_von_koeln(self):
        self.assertAlmostEqual(km(KOELN, BONN), 24.7, delta=1.0)

    def test_duesseldorf_liegt_ausserhalb(self):
        self.assertGreater(km(KOELN, DUESSELDORF), 30.0)


class EinordnenTest(unittest.TestCase):
    def test_remote_signal_schlaegt_entfernung(self):
        self.assertEqual(einordnen({"remote_signal": ["100% remote"], "km": 400}), "remote")

    def test_umkreisgrenze(self):
        self.assertEqual(einordnen({"km": 28.4}), "lokal")
        self.assertEqual(einordnen({"km": 33.7}), "raus")

    def test_abgelaufen_und_unklar(self):
        self.assertEqual(einordnen({"abgelaufen": True, "remote_signal": ["x"]}), "raus")
        self.assertEqual(einordnen({}), "offen")

    def test_fehlender_volltext_verwirft_nichts(self):
        self.assertEqual(einordnen({"titel_art": "allgemein", "fehler": "HTTP 429", "km": 5}), "offen")

    def test_linkedin_remote_ohne_zusage_im_text(self):
        self.assertEqual(einordnen({"quelle": "LinkedIn remote", "km": 390}), "remote_portal")

    def test_fach_bezug_zaehlt_erwaehnungen(self):
        self.assertEqual(fach_bezug("Datenschutz hier, DSGVO dort, Privacy überall"), 3)

    def test_fach_bezug_ohne_treffer(self):
        self.assertEqual(fach_bezug("Wir suchen jemanden für den Einkauf."), 0)


class SchluesselTest(unittest.TestCase):
    def test_gleiche_stelle_aus_zwei_quellen(self):
        a = {"firma": "FRANK GmbH", "titel": "Privacy Manager (m/w/d)", "url": "https://stepstone/1"}
        b = {"firma": "Frank GmbH", "titel": "Privacy Manager (m/w/d)", "url": "https://linkedin/2"}
        self.assertEqual(schluessel(a), schluessel(b))

    def test_ohne_firma_zaehlt_die_url(self):
        self.assertEqual(schluessel({"url": "https://x/1"}), "https://x/1")


if __name__ == "__main__":
    unittest.main()
