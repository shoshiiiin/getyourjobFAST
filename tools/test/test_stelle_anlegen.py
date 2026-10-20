import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import json  # noqa: E402

from stelle_anlegen import aus_laeufen, finden, ordnername, stelle_md  # noqa: E402
from tracker import stelle_lesen  # noqa: E402

JOB = {"titel": "Automation Specialist (m/w/d)", "firma": "Muster GmbH", "ort": "Remote",
       "quelle": "LinkedIn remote", "url": "https://de.linkedin.com/jobs/view/x-4473165768",
       "beschreibung": "Du baust Automationen.", "remote_signal": ["100 % remote"]}
TAG = dt.date(2026, 10, 9)


class OrdnerTest(unittest.TestCase):
    def test_name_ohne_rechtsform_und_geschlechtsangabe(self):
        self.assertEqual(ordnername(JOB, TAG), "2026-10-09-muster-automation-specialist")

    def test_umlaute_im_namen(self):
        job = {"firma": "Wirtschaftsförderung Frankfurt GmbH", "titel": "Projektmanager:in Digitalisierung"}
        self.assertEqual(ordnername(job, TAG), "2026-10-09-wirtschaftsfoerderung-frankfurt-projektmanager-digitalisierung")


class StelleMdTest(unittest.TestCase):
    def test_tracker_liest_was_hier_geschrieben_wird(self):
        with tempfile.TemporaryDirectory() as tmp:
            ordner = Path(tmp) / ordnername(JOB, TAG)
            ordner.mkdir()
            (ordner / "stelle.md").write_text(stelle_md(JOB, TAG), encoding="utf-8")
            daten = stelle_lesen(ordner)
        self.assertEqual(daten["firma"], "Muster GmbH")
        self.assertEqual(daten["rolle"], "Automation Specialist (m/w/d)")
        self.assertEqual(daten["url"], JOB["url"])
        self.assertEqual(daten["quelle"], "LinkedIn remote")


class FindenTest(unittest.TestCase):
    def test_eindeutig(self):
        self.assertIs(finden([JOB, {"firma": "Beispiel AG", "titel": "Manager Einkauf", "url": "u"}], "muster"), JOB)

    def test_findet_stelle_aus_aelterem_lauf(self):
        with tempfile.TemporaryDirectory() as tmp:
            alt, neu = Path(tmp) / "2026-10-09.json", Path(tmp) / "2026-10-12.json"
            alt.write_text(json.dumps({"treffer": [JOB]}), encoding="utf-8")
            neu.write_text(json.dumps({"treffer": []}), encoding="utf-8")
            self.assertEqual(aus_laeufen("muster", [alt, neu])["url"], JOB["url"])

    def test_mehrdeutig_bricht_ab(self):
        with self.assertRaises(SystemExit):
            finden([JOB, dict(JOB, url="u2")], "muster")


if __name__ == "__main__":
    unittest.main()
