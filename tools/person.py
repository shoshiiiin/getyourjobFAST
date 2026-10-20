"""
Zugriff auf profil/person.json und profil/suchmandat.json.

Alle persönlichen Angaben stehen genau dort — kein Werkzeug trägt sie im Code.
Fehlt eine Datei, bricht der Aufruf mit einer Anleitung ab statt mit KeyError.

Access to profil/person.json and profil/suchmandat.json: the only places where
personal details live. No tool hard-codes them.
"""
from __future__ import annotations

import functools
import json
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
PERSON = WURZEL / "profil" / "person.json"
MANDAT = WURZEL / "profil" / "suchmandat.json"

_FEHLT = (
    "{datei} fehlt.\n"
    "Lege sie an mit:  tools/.venv/bin/python tools/einrichten.py\n"
    "oder sage in Claude Code:  /einfuehrung"
)


def _laden(pfad: Path) -> dict:
    if not pfad.exists():
        raise SystemExit(_FEHLT.format(datei=pfad.relative_to(WURZEL)))
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"{pfad.relative_to(WURZEL)} ist kein gültiges JSON: {e}") from e


@functools.lru_cache(maxsize=1)
def person() -> dict:
    """Name, Kontakt, Anschrift, Wohnort, Suchradius."""
    d = _laden(PERSON)
    for feld in ("vorname", "nachname", "kontakt", "ort", "heimat"):
        if not d.get(feld):
            raise SystemExit(f"profil/person.json: Feld „{feld}“ fehlt oder ist leer.")
    return d


@functools.lru_cache(maxsize=1)
def mandat() -> dict:
    """Die regulären Ausdrücke, die festlegen, welche Stellen zählen."""
    return _laden(MANDAT)


def name() -> str:
    p = person()
    return f"{p['vorname']} {p['nachname']}"


def name_zeilen() -> list[str]:
    p = person()
    return [p["vorname"], p["nachname"]]


def datei_name() -> str:
    """Name für Dateinamen: „Alex_Beispiel“."""
    return name().replace(" ", "_")


def heimat() -> tuple[float, float]:
    lat, lon = person()["heimat"]
    return float(lat), float(lon)


def umkreis_km() -> float:
    return float(person().get("umkreis_km", 30))


def persoenlich() -> dict:
    """Der Block „Persönliches“ im Lebenslauf."""
    p = person()
    d = {"Name": name()}
    if p.get("anschrift"):
        d["Anschrift"] = p["anschrift"]
    if p.get("geburtsdatum"):
        d["Geburtsdatum"] = p["geburtsdatum"]
    d["Verfügbar ab"] = p.get("verfuegbar_ab", "sofort")
    return d
