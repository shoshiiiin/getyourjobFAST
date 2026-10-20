#!/usr/bin/env python3
"""
Einrichtung ohne Claude: fragt im Terminal das Nötigste ab und schreibt
profil/person.json, profil/suchmandat.json und tools/suchprofil.json.

    tools/.venv/bin/python tools/einrichten.py

Die inhaltlichen Dateien — profil/belege.md, profil/master-cv.md und
profil/lebenslauf-allgemein.json — füllst du danach von Hand aus. Wer Claude
Code hat, nimmt besser /einfuehrung: das führt ein Gespräch und schreibt auch
diese Dateien.

Setup without Claude: asks for the essentials and writes the three config
files. The content files are filled in by hand afterwards.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

WURZEL = Path(__file__).resolve().parent.parent
NOMINATIM = "https://nominatim.openstreetmap.org/search"
STANDARD_RADIUS = 30

T = {
    "sprache": ("Sprache / Language", "Sprache / Language"),
    "titel": ("getyourjob einrichten", "Setting up getyourjob"),
    "intro": (
        "Ich frage das Nötigste ab und schreibe daraus drei Dateien.\n"
        "Leer lassen übernimmt den Vorschlag in [Klammern].\n"
        "Abbrechen jederzeit mit Strg-C — geschrieben wird erst am Ende.",
        "I will ask for the essentials and write three files from the answers.\n"
        "Leave blank to accept the suggestion in [brackets].\n"
        "Cancel any time with Ctrl-C — nothing is written until the end.",
    ),
    "block_person": ("Zur Person", "About you"),
    "vorname": ("Vorname", "First name"),
    "nachname": ("Nachname", "Last name"),
    "email": ("E-Mail", "Email"),
    "telefon": ("Telefon", "Phone"),
    "strasse": ("Straße und Hausnummer", "Street and number"),
    "plz_ort": ("PLZ und Ort", "Postcode and city"),
    "web": ("Website (optional)", "Website (optional)"),
    "linkedin": ("LinkedIn-Profil, nur der Pfad (optional)", "LinkedIn profile, path only (optional)"),
    "geburt": ("Geburtsdatum TT.MM.JJJJ (optional)", "Date of birth DD.MM.YYYY (optional)"),
    "verfuegbar": ("Verfügbar ab", "Available from"),
    "block_ort": ("Ort und Umkreis", "Location and radius"),
    "wohnort": ("Wohnort (Stadt)", "Home city"),
    "radius": ("Wie viele Kilometer würdest du pendeln?", "How many kilometres would you commute?"),
    "geo_suche": ("Suche Koordinaten für", "Looking up coordinates for"),
    "geo_ok": ("gefunden", "found"),
    "geo_fehler": (
        "Nicht gefunden. Gib die Koordinaten von Hand ein (z. B. aus OpenStreetMap).",
        "Not found. Enter the coordinates by hand (for example from OpenStreetMap).",
    ),
    "lat": ("Breitengrad", "Latitude"),
    "lon": ("Längengrad", "Longitude"),
    "block_mandat": ("Dein Mandat", "Your mandate"),
    "rollen": (
        "Wunschrollen, durch Komma getrennt\n  (z. B. Projektmanager, Prozessmanager, Business Analyst)",
        "Target roles, comma separated\n  (e.g. Project Manager, Process Manager, Business Analyst)",
    ),
    "fach": (
        "Dein Fachgebiet in Stichworten, durch Komma getrennt\n"
        "  (z. B. Digitalisierung, Prozesse, Projektmanagement)",
        "Your field in keywords, comma separated\n  (e.g. digitalisation, processes, project management)",
    ),
    "raus": (
        "Was ausdrücklich nicht? Durch Komma getrennt\n  (z. B. Vertrieb, Recruiting, Entwicklung)",
        "What is explicitly out? Comma separated\n  (e.g. sales, recruiting, development)",
    ),
    "vertraulich": (
        "Kundennamen unter NDA, die nirgends auftauchen dürfen (optional, Komma)",
        "Client names under NDA that must never appear (optional, comma)",
    ),
    "block_schreiben": ("Schreiben", "Writing"),
    "ueberschreiben": (
        "{datei} enthält schon Daten. Überschreiben?",
        "{datei} already holds data. Overwrite?",
    ),
    "uebersprungen": ("übersprungen", "skipped"),
    "fertig": ("Fertig. Als Nächstes:", "Done. Next:"),
    "naechste": (
        "  1. profil/belege.md füllen — jede Zahl, die du behaupten darfst\n"
        "  2. profil/master-cv.md füllen — deine Laufbahn als Fließtext\n"
        "  3. profil/lebenslauf-allgemein.json füllen — der Lebenslauf als Daten\n"
        "  4. Probelauf: tools/.venv/bin/python tools/stellensuche.py --tage 7",
        "  1. Fill profil/belege.md — every number you may claim\n"
        "  2. Fill profil/master-cv.md — your career history in prose\n"
        "  3. Fill profil/lebenslauf-allgemein.json — the CV as data\n"
        "  4. Try a run: tools/.venv/bin/python tools/stellensuche.py --tage 7",
    ),
    "ja": ("j", "y"),
}

SPRACHE = 0  # 0 = deutsch, 1 = englisch


def t(schluessel: str, **kw) -> str:
    return T[schluessel][SPRACHE].format(**kw)


def frage(schluessel: str, standard: str = "", pflicht: bool = False,
          pruefen: Callable[[str], str | None] | None = None) -> str:
    """Eine Frage, bis eine gültige Antwort kommt. Leer nimmt den Standard."""
    etikett = t(schluessel)
    while True:
        zusatz = f" [{standard}]" if standard else ""
        antwort = input(f"  {etikett}{zusatz}: ").strip() or standard
        if not antwort and pflicht:
            continue
        if pruefen and antwort:
            fehler = pruefen(antwort)
            if fehler:
                print(f"    → {fehler}")
                continue
        return antwort


def ja_nein(text: str, standard: bool = False) -> bool:
    ja = T["ja"][SPRACHE]
    nein = "n"
    vorschlag = f"{ja.upper()}/{nein}" if standard else f"{ja}/{nein.upper()}"
    antwort = input(f"  {text} [{vorschlag}]: ").strip().lower()
    return standard if not antwort else antwort.startswith(ja)


def block(schluessel: str) -> None:
    print(f"\n\033[1m{t(schluessel)}\033[0m")


def mail_pruefen(s: str) -> str | None:
    return None if re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}", s) else "Keine gültige E-Mail-Adresse."


def zahl_pruefen(s: str) -> str | None:
    try:
        float(s.replace(",", "."))
        return None
    except ValueError:
        return "Bitte eine Zahl."


def geokodieren(ort: str) -> tuple[float, float] | None:
    """Koordinaten über Nominatim. Gibt None zurück, wenn nichts gefunden wird."""
    frage_url = f"{NOMINATIM}?{urllib.parse.urlencode({'q': ort, 'format': 'json', 'limit': 1})}"
    bitte = urllib.request.Request(frage_url, headers={"User-Agent": "getyourjob-setup/1.0"})
    try:
        with urllib.request.urlopen(bitte, timeout=15) as antwort:  # noqa: S310
            treffer = json.load(antwort)
    except Exception:
        return None
    if not treffer:
        return None
    return round(float(treffer[0]["lat"]), 4), round(float(treffer[0]["lon"]), 4)


def liste(roh: str) -> list[str]:
    return [s.strip() for s in roh.split(",") if s.strip()]


def als_regex(begriffe: list[str]) -> str:
    """Begriffe zu einem Alternativ-Regex, Endungen bleiben offen."""
    teile = [re.escape(b.lower()).replace(r"\ ", r"\s*") for b in begriffe]
    return "(" + "|".join(teile) + ")" if teile else "(?!)"


def schreiben(pfad: Path, inhalt: str, beispiel_marker: str) -> bool:
    """Schreibt, fragt aber nach, wenn die Datei keine Beispieldaten mehr enthält."""
    if pfad.exists() and beispiel_marker not in pfad.read_text(encoding="utf-8"):
        if not ja_nein(t("ueberschreiben", datei=pfad.relative_to(WURZEL))):
            print(f"    {pfad.relative_to(WURZEL)} — {t('uebersprungen')}")
            return False
    pfad.write_text(inhalt, encoding="utf-8")
    print(f"    {pfad.relative_to(WURZEL)}")
    return True


def main() -> None:
    global SPRACHE
    wahl = input(f"  {T['sprache'][0]} [de/en]: ").strip().lower()
    SPRACHE = 1 if wahl.startswith("e") else 0

    print(f"\n\033[1m{t('titel')}\033[0m\n{t('intro')}")

    block("block_person")
    vorname = frage("vorname", pflicht=True)
    nachname = frage("nachname", pflicht=True)
    email = frage("email", pflicht=True, pruefen=mail_pruefen)
    telefon = frage("telefon")
    strasse = frage("strasse")
    plz_ort = frage("plz_ort")
    web = frage("web")
    linkedin = frage("linkedin")
    geburt = frage("geburt")
    verfuegbar = frage("verfuegbar", "sofort" if SPRACHE == 0 else "immediately")

    block("block_ort")
    wohnort = frage("wohnort", pflicht=True)
    radius = frage("radius", str(STANDARD_RADIUS), pruefen=zahl_pruefen)
    print(f"    {t('geo_suche')} „{wohnort}“ …")
    koordinaten = geokodieren(f"{wohnort}, Deutschland") or geokodieren(wohnort)
    if koordinaten:
        print(f"    {koordinaten[0]}, {koordinaten[1]} — {t('geo_ok')}")
    else:
        print(f"    {t('geo_fehler')}")
        koordinaten = (float(frage("lat", pflicht=True, pruefen=zahl_pruefen).replace(",", ".")),
                       float(frage("lon", pflicht=True, pruefen=zahl_pruefen).replace(",", ".")))

    block("block_mandat")
    rollen = liste(frage("rollen", pflicht=True))
    fach = liste(frage("fach", pflicht=True))
    raus = liste(frage("raus"))
    vertraulich = liste(frage("vertraulich"))

    kontakt: list = [[telefon, email]] if telefon else [[email, ""]]
    if web:
        kontakt.append(web)
    if linkedin:
        kontakt.append(f"linkedin: {linkedin}")

    person = {
        "_hinweis": "Die einzige Datei mit persönlichen Angaben. | The only file holding personal details.",
        "vorname": vorname, "nachname": nachname, "kontakt": kontakt,
        "anschrift": f"{strasse}\n{plz_ort}" if strasse or plz_ort else "",
        "geburtsdatum": geburt, "verfuegbar_ab": verfuegbar,
        "ort": wohnort, "ort_linkedin": f"{wohnort}, Deutschland",
        "heimat": [koordinaten[0], koordinaten[1]],
        "umkreis_km": float(radius.replace(",", ".")),
        "_wettbewerb": "Optional: Themen zu nah an der eigenen Firma (Regex). Leer = Prüfung aus.",
        "wettbewerb": "",
        "_vertraulich": "Wörter, die in keinem Dokument stehen dürfen.",
        "vertraulich": vertraulich,
    }

    mandat = {
        "_hinweis": "Welche Stellen zählen. Reguläre Ausdrücke, Groß-/Kleinschreibung egal.",
        "titel_ausschluss": ("(werkstudent|working student|\\bintern\\b|internship|praktik|trainee|"
                             "ausbildung|azubi|duales|thesis|abschlussarbeit|freelance|freiberuf|minijob"
                             + ("|" + "|".join(re.escape(r.lower()) for r in raus) if raus else "") + ")"),
        "titel_kern": als_regex(rollen),
        "titel_allgemein": "(consultant|berater|manager|koordinator|referent|specialist|spezialist|analyst)",
        "fach_ausschluss": als_regex(raus) if raus else "(?!)",
        "kern_wort": als_regex(fach),
    }

    suchprofil = {
        "_hinweis": "Suchbegriffe für tools/stellensuche.py.",
        "suchbegriffe": rollen + fach,
        "stepstone_seiten": 1, "linkedin_seiten": 2,
        "orte": [wohnort],
        "ausschluss": ["Ausbildung", "Auszubildende", "Azubi", "Werkstudent",
                       "Praktikum", "Praktikant", "Trainee", "Duales Studium", "Minijob"],
    }

    block("block_schreiben")
    schreiben(WURZEL / "profil/person.json",
              json.dumps(person, ensure_ascii=False, indent=2) + "\n", "Alex")
    schreiben(WURZEL / "profil/suchmandat.json",
              json.dumps(mandat, ensure_ascii=False, indent=2) + "\n", "projektmanag")
    schreiben(WURZEL / "tools/suchprofil.json",
              json.dumps(suchprofil, ensure_ascii=False, indent=2) + "\n", "Projektmanager")

    print(f"\n\033[1m{t('fertig')}\033[0m\n{t('naechste')}")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nAbgebrochen. Es wurde nichts geschrieben. / Cancelled, nothing written.")
        sys.exit(130)
