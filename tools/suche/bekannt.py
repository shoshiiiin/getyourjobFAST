"""
Was die Suche nicht noch einmal vorschlagen soll.

- Firmen aus dem Tracker (Mandat: keine Dubletten) und aus stellen/*/stelle.md
- Personaldienstleister und eigene Sperrliste (ausschluss.json)
- Anzeigen, die schon in einem früheren Suchlauf standen (gesehen.json, per URL)
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tracker import DATEI as TRACKER, gleiche_firma, stelle_lesen  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent
AUSSCHLUSS = Path(__file__).with_name("ausschluss.json")
GESEHEN = WURZEL / "stellen" / "suchlaeufe" / "gesehen.json"
URL = re.compile(r"https?://[^\s)|>\]]+")


def firmen_im_tracker() -> list[str]:
    if not TRACKER.exists():
        return []
    import openpyxl

    ws = openpyxl.load_workbook(TRACKER, read_only=True, data_only=True)["Bewerbungen"]
    return [r[0] for r in ws.iter_rows(min_row=3, min_col=3, max_col=3, values_only=True) if isinstance(r[0], str)]


VERMITTLER = re.compile(r"(recruit|personalberatung|personaldienst|staffing|headhunt|talent solutions|zeitarbeit)", re.I)


def _voll(name: str) -> str:
    t = (name or "").lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]", "", t)


def gesperrte_firmen() -> dict[str, list[str]]:
    """eigene: Tracker + Stellenordner + Sperrliste · vermittler: Personaldienstleister."""
    liste = json.loads(AUSSCHLUSS.read_text(encoding="utf-8"))
    eigene = list(firmen_im_tracker()) + liste["firmen"]
    for ordner in (WURZEL / "stellen").glob("20*-*"):
        firma = stelle_lesen(ordner).get("firma")
        if firma:
            eigene.append(firma)
    return {"eigene": eigene, "vermittler": [_voll(v) for v in liste["personaldienstleister"]]}


def gesperrt(firma: str, sperre: dict[str, list[str]]) -> bool:
    if VERMITTLER.search(firma or ""):
        return True
    voll = _voll(firma)
    if any(len(v) >= 4 and voll.startswith(v) for v in sperre["vermittler"]):
        return True
    return any(gleiche_firma(firma, f) for f in sperre["eigene"])


def gesehen_laden() -> dict[str, str]:
    """URL → Datum des ersten Auftauchens. Beim ersten Aufruf aus den alten Suchläufen befüllt."""
    if GESEHEN.exists():
        return json.loads(GESEHEN.read_text(encoding="utf-8"))
    alt: dict[str, str] = {}
    for datei in list((WURZEL / "stellen-remote").glob("*")) + list((WURZEL / "stellen").glob("*/stelle.md")):
        if datei.suffix in (".md", ".json"):
            for url in URL.findall(datei.read_text(encoding="utf-8", errors="replace")):
                alt.setdefault(url.rstrip(".,"), "vor 2026-10-09")
    return alt


def gesehen_speichern(gesehen: dict[str, str], neue_urls: list[str]) -> None:
    heute = dt.date.today().isoformat()
    for url in neue_urls:
        gesehen.setdefault(url, heute)
    GESEHEN.parent.mkdir(parents=True, exist_ok=True)
    GESEHEN.write_text(json.dumps(gesehen, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
