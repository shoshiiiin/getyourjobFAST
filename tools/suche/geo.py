"""Entfernung einer Ortsangabe zum eigenen Ort (profil/person.json), über Nominatim (OpenStreetMap) mit Dateicache."""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from .filter import HEIMAT, km, orte

CACHE = Path(__file__).with_name("geo_cache.json")
NOMINATIM = "https://nominatim.openstreetmap.org/search?"
AGENT = "bewerbungen-umkreis/1.0 (private Stellensuche)"


class Geo:
    def __init__(self, cache: Path = CACHE):
        self.cache_datei = cache
        self.cache: dict = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}

    def koordinaten(self, ort: str) -> list[float] | None:
        if ort in self.cache:
            return self.cache[ort]
        q = urllib.parse.urlencode({"q": f"{ort}, Deutschland", "format": "json", "limit": 1, "countrycodes": "de"})
        try:
            with urllib.request.urlopen(urllib.request.Request(NOMINATIM + q, headers={"User-Agent": AGENT}), timeout=20) as r:
                antwort = json.load(r)
            wert = [float(antwort[0]["lat"]), float(antwort[0]["lon"])] if antwort else None
        except (OSError, ValueError):
            return None  # nicht cachen: beim nächsten Lauf neu versuchen
        self.cache[ort] = wert
        time.sleep(1.1)  # Nominatim erlaubt höchstens eine Anfrage je Sekunde
        return wert

    def naechster(self, ortsangabe: str) -> tuple[float, str] | None:
        """Kleinste Entfernung über alle genannten Orte, gerundet auf 0,1 km."""
        best = None
        for o in orte(ortsangabe):
            c = self.koordinaten(o)
            if c:
                d = round(km(HEIMAT, tuple(c)), 1)
                if best is None or d < best[0]:
                    best = (d, o)
        return best

    def speichern(self) -> None:
        self.cache_datei.write_text(json.dumps(self.cache, ensure_ascii=False, indent=1), encoding="utf-8")
