"""
Reine Filterlogik der Stellensuche: kein Netz, keine Dateien.

Was als passende Stelle gilt, steht nicht hier, sondern in profil/suchmandat.json
und profil/person.json. Dieses Modul kennt nur die Mechanik: Titel prüfen,
Entfernung rechnen, Remote-Signale erkennen, Dubletten finden.

Pure filtering logic: no network, no files. The mandate itself lives in
profil/suchmandat.json; this module only provides the mechanics.
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import person as _person  # noqa: E402

HEIMAT = _person.heimat()
UMKREIS_KM = _person.umkreis_km()

# Die vier Mandats-Regexe stehen in profil/suchmandat.json. setze_mandat() lädt
# sie neu — Tests rufen das mit einem eigenen Mandat auf, damit sie unabhängig
# davon laufen, was gerade im Profil steht.
TITEL_SCHLECHT = TITEL_KERN = TITEL_ALLGEMEIN = FACH_RAUS = FACH_WORT = None


def setze_mandat(mandat: dict) -> None:
    """Übernimmt ein Mandat (profil/suchmandat.json oder eines aus einem Test)."""
    global TITEL_SCHLECHT, TITEL_KERN, TITEL_ALLGEMEIN, FACH_RAUS, FACH_WORT
    TITEL_SCHLECHT = re.compile(mandat["titel_ausschluss"], re.I)   # fällt sofort raus
    TITEL_KERN = re.compile(mandat["titel_kern"], re.I)             # passt ohne weitere Prüfung
    TITEL_ALLGEMEIN = re.compile(mandat["titel_allgemein"], re.I)   # zählt nur mit Fachbezug im Text
    FACH_RAUS = re.compile(mandat["fach_ausschluss"], re.I)         # fremdes Fachgebiet
    FACH_WORT = re.compile(mandat["kern_wort"], re.I)               # Fachbezug im Anzeigentext


def setze_heimat(koordinaten: tuple[float, float], umkreis_km: float) -> None:
    """Setzt Wohnort und Radius. Tests nutzen das, um nicht vom Profil abzuhängen."""
    global HEIMAT, UMKREIS_KM
    HEIMAT, UMKREIS_KM = koordinaten, umkreis_km


setze_mandat(_person.mandat())

REMOTE_VOLL = re.compile(
    r"(100\s?%\s?(remote|home.?office|mobil)|vollständig (remote|mobil|von zu ?hause|aus dem home)|"
    r"komplett (remote|mobil|aus dem home)|fully remote|full(y)?[- ]remote|remote[- ]first|"
    r"remote only|remote-only|ausschließlich (remote|mobil)|deutschlandweit remote|"
    r"remote (in|within|from anywhere in) germany|remote.{0,20}deutschlandweit|ortsunabhängig|"
    r"work from anywhere in germany|standortunabhängig|100 ?% mobile)",
    re.I,
)
HYBRID = re.compile(
    r"(hybrid|\d\s?(tage|days).{0,30}(büro|office|vor ort)|(bis zu|up to) \d{1,2}\s?%|präsenz|"
    r"on-?site|vor ort beim kunden|reisebereitschaft|travel)",
    re.I,
)
ORT_RAUSCHEN = re.compile(
    r"\b(Germany|Deutschland|Hesse|Hessen|Rhineland-Palatinate|Rheinland-Pfalz|Metropolitan Area|"
    r"Region|Area|Home-Office|Homeoffice|bundesweit|Remote)\b",
    re.I,
)


def titel_art(titel: str) -> str | None:
    """„kern“ (Titel passt klar), „allgemein“ (Bezug erst im Text prüfen) oder None (raus)."""
    if not titel or TITEL_SCHLECHT.search(titel) or FACH_RAUS.search(titel):
        return None
    if TITEL_KERN.search(titel):
        return "kern"
    return "allgemein" if TITEL_ALLGEMEIN.search(titel) else None


def titel_passt(titel: str) -> bool:
    return titel_art(titel) is not None


def fach_bezug(text: str) -> int:
    """Wie oft die Anzeige das eigene Fach erwähnt (profil/suchmandat.json → kern_wort)."""
    return len(FACH_WORT.findall(text or ""))


ki_bezug = fach_bezug  # alter Name, bleibt gültig


def signale(text: str, muster: re.Pattern, grenze: int = 3) -> list[str]:
    """Bis zu `grenze` verschiedene Fundstellen eines Musters, in Reihenfolge."""
    gefunden: list[str] = []
    for m in muster.finditer(text or ""):
        wort = m.group(0).strip()
        if wort.lower() not in (g.lower() for g in gefunden):
            gefunden.append(wort)
        if len(gefunden) == grenze:
            break
    return gefunden


def orte(ortsangabe: str) -> list[str]:
    """Zerlegt eine Ortsangabe wie „Eschborn, Hessen, Deutschland“ in geokodierbare Teile."""
    s = ORT_RAUSCHEN.sub("", ortsangabe or "")
    s = re.sub(r"\bbei\b.*", "", s)
    teile = [t.strip(" ,()") for t in re.split(r"[,/;]|\s\+\s", s)]
    return [t for t in teile if len(t) > 2 and not t.isdigit()]


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Luftlinie in Kilometern (Haversine)."""
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def schluessel(job: dict) -> str:
    """Dublettenschlüssel über Quellen hinweg: Firma + Titelanfang, sonst URL."""
    def n(s: str) -> str:
        return re.sub(r"[^a-z0-9]", "", (s or "").lower())

    return f"{n(job.get('firma', ''))[:12]}|{n(job.get('titel', ''))[:24]}" if job.get("firma") else job.get("url", "")


def einordnen(job: dict) -> str:
    """
    remote        ausdrücklich voll remote im Anzeigentext
    lokal         höchstens UMKREIS_KM vom eigenen Ort
    remote_portal laut LinkedIn-Filter remote, im Text nicht bestätigt
    offen         Ort nicht bestimmbar
    raus          abgelaufen, zu weit weg oder allgemeine Rolle ohne Fachbezug
    """
    if job.get("abgelaufen"):
        return "raus"
    if job.get("fehler") and not job.get("beschreibung"):
        return "offen"  # Volltext fehlt: nicht verwerfen, beim nächsten Lauf neu versuchen
    if job.get("titel_art") == "allgemein" and fach_bezug(job.get("beschreibung", "")) < 2:
        return "raus"
    if job.get("remote_signal"):
        return "remote"
    entfernung = job.get("km")
    if entfernung is not None and entfernung <= UMKREIS_KM:
        return "lokal"
    if job.get("quelle") == "LinkedIn remote":
        return "remote_portal"
    return "offen" if entfernung is None else "raus"
