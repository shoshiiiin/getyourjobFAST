import contextlib
import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import person  # noqa: E402
from bewerbung import anschreiben, datum_de, lebenslauf, pruefen, woerter  # noqa: E402

BRIEF = {"empfaenger": ["Muster GmbH"], "betreff": "Bewerbung als Prozessmanager", "anrede": "Hallo Team,",
         "absaetze": ["Ein Absatz mit Beleg."], "bullets": ["Punkt eins"], "schluss": "Start sofort."}
CV = {"profil": ["Profiltext"], "kernkompetenzen": [{"titel": "A", "inhalt": "B"}]}
BASIS = {"nameLines": ["Alex", "Beispiel"], "kontakt": ["x"], "zertifikate": ["z0", "z1", "z2"],
         "erfahrungen": [{"bullets": [f"g{i}" for i in range(7)]}, {"bullets": [f"d{i}" for i in range(5)]}]}


@contextlib.contextmanager
def geheim(*woerter):
    """Setzt profil/person.json → vertraulich für die Dauer des Tests."""
    echt = person.person
    person.person = lambda: {**echt(), "vertraulich": list(woerter)}
    try:
        yield
    finally:
        person.person = echt


class PruefenTest(unittest.TestCase):
    def test_vollstaendiger_entwurf_ist_ok(self):
        self.assertEqual(pruefen({"kuerzel": "MUSTER", "brief": BRIEF, "lebenslauf": CV}), [])

    def test_zu_langer_brief(self):
        lang = dict(BRIEF, absaetze=["wort " * 240])
        self.assertTrue(any("Wörter" in f for f in pruefen({"kuerzel": "X1", "brief": lang, "lebenslauf": CV})))

    def test_selbstsabotage_wird_erkannt(self):
        b = dict(BRIEF, absaetze=["Ein abgeschlossenes Studium habe ich nicht."])
        self.assertTrue(pruefen({"kuerzel": "X1", "brief": b, "lebenslauf": CV}))

    def test_vertrauliches_wort_im_brief(self):
        with geheim("GEHEIMKUNDE"):
            b = dict(BRIEF, absaetze=["Für GEHEIMKUNDE habe ich geliefert."])
            fehler = pruefen({"kuerzel": "X1", "brief": b, "lebenslauf": CV})
        self.assertTrue(any("GEHEIMKUNDE" in f for f in fehler), fehler)

    def test_vertrauliches_wort_auch_im_lebenslauf(self):
        with geheim("GEHEIMKUNDE"):
            cv = dict(CV, kernkompetenzen=[{"titel": "Projekt", "inhalt": "Umbau für GEHEIMKUNDE"}])
            self.assertTrue(pruefen({"kuerzel": "X1", "brief": BRIEF, "lebenslauf": cv}))

    def test_ohne_anschreiben_braucht_keinen_brief(self):
        self.assertEqual(pruefen({"kuerzel": "MUSTER", "ohne_anschreiben": True, "lebenslauf": CV}), [])

    def test_kuerzel_pflicht(self):
        self.assertIn("kuerzel", pruefen({"brief": BRIEF, "lebenslauf": CV})[0])


class BauenTest(unittest.TestCase):
    def test_woerter_zaehlt_absaetze_bullets_schluss(self):
        self.assertEqual(woerter(BRIEF), 4 + 2 + 2)

    def test_datum_deutsch(self):
        self.assertEqual(datum_de(dt.date(2026, 10, 9)), "9. Oktober 2026")

    def test_lebenslauf_waehlt_bullets_und_laesst_vorlage_unberuehrt(self):
        d = lebenslauf(BASIS, dict(CV, gruender=[0, 6], dozent=[1], zertifikate=[2]))
        self.assertEqual(d["erfahrungen"][0]["bullets"], ["g0", "g6"])
        self.assertEqual(d["zertifikate"], ["z2"])
        self.assertEqual(len(BASIS["erfahrungen"][0]["bullets"]), 7)

    def test_anschreiben_macht_bullet_block(self):
        b = anschreiben(BASIS, dict(BRIEF, bullet_titel="Was ich übernehme:"), dt.date(2026, 10, 9), englisch=False)
        self.assertEqual(b["bulletBlock"], {"titel": "Was ich übernehme:", "punkte": ["Punkt eins"]})
        self.assertNotIn("bullets", b)
        self.assertEqual(b["datum"], "9. Oktober 2026")


if __name__ == "__main__":
    unittest.main()
