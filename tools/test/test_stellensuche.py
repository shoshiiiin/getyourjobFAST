import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from stellensuche import ohne_volltext, zusammenfuehren  # braucht scrapling (tools/.venv)
except ImportError:  # pragma: no cover
    zusammenfuehren = None


@unittest.skipIf(zusammenfuehren is None, "scrapling fehlt")
class GleicherTagTest(unittest.TestCase):
    def test_zweiter_lauf_ergaenzt_den_ersten(self):
        with tempfile.TemporaryDirectory() as tmp:
            datei = Path(tmp) / "2026-10-09.json"
            datei.write_text(json.dumps({"treffer": [{"url": "a", "einordnung": "lokal"}]}), encoding="utf-8")
            zusammen = zusammenfuehren(datei, [{"url": "b", "einordnung": "remote"}])
        self.assertEqual([j["url"] for j in zusammen], ["a", "b"])

    def test_neuer_stand_ersetzt_alten_derselben_anzeige(self):
        with tempfile.TemporaryDirectory() as tmp:
            datei = Path(tmp) / "x.json"
            datei.write_text(json.dumps({"treffer": [{"url": "a", "einordnung": "offen"}]}), encoding="utf-8")
            zusammen = zusammenfuehren(datei, [{"url": "a", "einordnung": "lokal"}])
        self.assertEqual(zusammen, [{"url": "a", "einordnung": "lokal"}])

    def test_ohne_datei_bleibt_alles(self):
        self.assertEqual(zusammenfuehren(Path("/nicht/da.json"), [{"url": "a"}]), [{"url": "a"}])

    def test_volltext_fehlt(self):
        self.assertTrue(ohne_volltext({"fehler": "HTTP 429"}))
        self.assertFalse(ohne_volltext({"fehler": "x", "beschreibung": "Text"}))


if __name__ == "__main__":
    unittest.main()
