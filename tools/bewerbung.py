#!/usr/bin/env python3
"""
Baut aus stellen/<ordner>/entwurf.json die fertige Bewerbung.

    tools/.venv/bin/python tools/bewerbung.py stellen/<ordner> [--ohne-tracker]

entwurf.json (schreibt Claude nach analyse.md):

    {
      "kuerzel": "MUSTER",                   # für die Dateinamen
      "sprache": "de",                       # "en" nimmt den englischen Lebenslauf
      "ohne_anschreiben": false,             # true, wenn die Anzeige keins will
      "brief": {"empfaenger": [...], "betreff": "...", "anrede": "...",
                "absaetze": [...], "bullet_titel": "...", "bullets": [...],
                "schluss": "...", "gruss": "Mit freundlichen Grüßen"},
      "lebenslauf": {"profil": [...], "kernkompetenzen": [{"titel": "...", "inhalt": "..."}],
                     "gruender": [0, 1, 2, 6], "dozent": [0, 1, 2, 4], "zertifikate": [0, 2]}
    }

Ergebnis im Ordner: anschreiben.json, lebenslauf.json, Anschreiben_…pdf,
Lebenslauf_…pdf, Stellenanzeige.pdf und eine Zeile „Vorbereitet“ im Tracker.
Bricht ab, wenn der Brief über 230 Wörter hat, eine verbotene Wendung aus
profil/stil.md enthält oder ein PDF nicht frisch geschrieben wurde.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

import person as _person

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parent
WORT_MAX = 230
FOTO = "../../profil/anlagen/bewerbungsfoto.jpg"
MONATE = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
          "September", "Oktober", "November", "Dezember")
# profil/stil.md, Abschnitt „Verboten“: Wendungen, die den Brief schwächen.
# Dazu kommen die Wörter aus profil/person.json → "vertraulich" (etwa Kundennamen unter NDA).
VERBOTEN = [
    (r"bringe ich nicht mit", "„X bringe ich nicht mit“"),
    (r"(müsste|wäre) .{0,40}(erarbeiten|lernen)", "„das müsste ich lernen“"),
    (r"(Studium|Abschluss) habe ich nicht", "fehlenden Abschluss thematisieren"),
    (r"(bisher|noch) nicht (mit|damit) gearbeitet", "fehlende Werkzeugpraxis thematisieren"),
    (r"^(Offen gesagt|Zur Offenheit gehört|Ein Hinweis in eigener Sache|Klar benannt)", "Offenheits-Einstieg"),
    (r"hiermit bewerbe ich mich", "„hiermit bewerbe ich mich“"),
    (r"Sehr geehrte Damen und Herren", "„Sehr geehrte Damen und Herren“"),
]


def verboten() -> list[tuple[str, str]]:
    """Die festen Wendungen plus die vertraulichen Wörter aus profil/person.json."""
    geheim = [(rf"\b{re.escape(w)}\b", f"vertrauliches Wort „{w}“ genannt")
              for w in _person.person().get("vertraulich", []) if w.strip()]
    return geheim + VERBOTEN


def woerter(brief: dict) -> int:
    texte = list(brief.get("absaetze", [])) + list(brief.get("bullets", [])) + [brief.get("schluss", "")]
    return sum(len(t.split()) for t in texte)


def pruefen(entwurf: dict) -> list[str]:
    """Alle Einwände gegen einen Entwurf; leer heißt: darf gebaut werden."""
    fehler = []
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{1,24}", entwurf.get("kuerzel", "")):
        fehler.append("kuerzel fehlt oder ist nicht GROSS_GESCHRIEBEN (A–Z, 0–9, _ -)")
    cv = entwurf.get("lebenslauf") or {}
    for k in ("profil", "kernkompetenzen"):
        if not cv.get(k):
            fehler.append(f"lebenslauf.{k} fehlt")
    if not entwurf.get("ohne_anschreiben"):
        brief = entwurf.get("brief") or {}
        for k in ("empfaenger", "betreff", "anrede", "absaetze", "schluss"):
            if not brief.get(k):
                fehler.append(f"brief.{k} fehlt")
        n = woerter(brief)
        if n > WORT_MAX:
            fehler.append(f"Brief hat {n} Wörter, erlaubt sind {WORT_MAX} (sonst Seite 2)")
        text = "\n".join([brief.get("anrede", "")] + list(brief.get("absaetze", []))
                         + list(brief.get("bullets", [])) + [brief.get("schluss", "")])
        fehler += [f"Verboten: {grund}" for muster, grund in verboten() if re.search(muster, text, re.I | re.M)]
    cv_text = "\n".join(list(cv.get("profil", [])) + [f"{k.get('titel', '')} {k.get('inhalt', '')}"
                                                       for k in cv.get("kernkompetenzen", [])])
    geheim = [(m, g) for m, g in verboten() if "vertrauliches Wort" in g]
    fehler += [f"Verboten im Lebenslauf: {grund}" for muster, grund in geheim if re.search(muster, cv_text, re.I)]
    return fehler


def datum_de(tag: dt.date) -> str:
    return f"{tag.day}. {MONATE[tag.month - 1]} {tag.year}"


def lebenslauf(basis: dict, wahl: dict) -> dict:
    d = json.loads(json.dumps(basis))  # tiefe Kopie, die Vorlage bleibt unberührt
    d["foto"] = FOTO
    d["nameLines"] = _person.name_zeilen()
    d["kontakt"] = _person.person()["kontakt"]
    d["persoenlich"] = _person.persoenlich()
    d["profil"] = wahl["profil"]
    d["kernkompetenzen"] = wahl["kernkompetenzen"]
    d["zertifikate"] = [d["zertifikate"][i] for i in wahl.get("zertifikate", (0, 2))]
    for nr, schluessel in ((0, "gruender"), (1, "dozent")):
        auswahl = wahl.get(schluessel, (0, 1, 2, 4))
        d["erfahrungen"][nr]["bullets"] = [d["erfahrungen"][nr]["bullets"][i] for i in auswahl]
    return d


def anschreiben(basis: dict, brief: dict, heute: dt.date, englisch: bool) -> dict:
    b = {"foto": FOTO, "nameLines": _person.name_zeilen(), "kontakt": _person.person()["kontakt"],
         "ort": _person.person()["ort"],
         "datum": f"{heute.day} {heute.strftime('%B %Y')}" if englisch else datum_de(heute),
         "signatur": _person.name(), "gruss": "Kind regards" if englisch else "Mit freundlichen Grüßen"}
    b.update({k: v for k, v in brief.items() if k not in ("bullet_titel", "bullets")})
    if brief.get("bullets"):
        b["bulletBlock"] = {"titel": brief.get("bullet_titel", ""), "punkte": brief["bullets"]}
    return b


def rendern(skript: str, quelle: Path, ziel: Path) -> str:
    p = subprocess.run(["node", str(HIER / skript), str(quelle), str(ziel)], cwd=WURZEL,
                       capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise SystemExit(f"{skript} fehlgeschlagen:\n{p.stderr.strip()}")
    if not ziel.exists() or ziel.stat().st_mtime < quelle.stat().st_mtime:
        raise SystemExit(f"{ziel.name} ist älter als {quelle.name} — Render hat nicht geschrieben")
    return (p.stdout + p.stderr).strip()


def bauen(ordner: Path, mit_tracker: bool = True) -> None:
    entwurf = json.loads((ordner / "entwurf.json").read_text(encoding="utf-8"))
    einwaende = pruefen(entwurf)
    if einwaende:
        raise SystemExit("Entwurf nicht gebaut:\n- " + "\n- ".join(einwaende))
    englisch = entwurf.get("sprache") == "en"
    basis = json.loads((WURZEL / "profil" / ("lebenslauf-allgemein-en.json" if englisch else "lebenslauf-allgemein.json"))
                       .read_text(encoding="utf-8"))
    k = entwurf["kuerzel"]
    wer = _person.datei_name()
    meldungen = []

    cv = ordner / "lebenslauf.json"
    cv.write_text(json.dumps(lebenslauf(basis, entwurf["lebenslauf"]), ensure_ascii=False, indent=2), encoding="utf-8")
    meldungen.append(rendern("render-cv-allgemein.mjs", cv, ordner / f"{'CV' if englisch else 'Lebenslauf'}_{wer}_{k}.pdf"))
    if not entwurf.get("ohne_anschreiben"):
        brief = ordner / "anschreiben.json"
        brief.write_text(json.dumps(anschreiben(basis, entwurf["brief"], dt.date.today(), englisch),
                                    ensure_ascii=False, indent=2), encoding="utf-8")
        aus = rendern("render-anschreiben.mjs", brief, ordner / f"{'Cover_Letter' if englisch else 'Anschreiben'}_{wer}_{k}.pdf")
        seiten = re.search(r"— (\d+) Seite", aus)
        if seiten and int(seiten.group(1)) > 1:
            raise SystemExit(f"Anschreiben läuft auf {seiten.group(1)} Seiten — Text kürzen\n{aus}")
        meldungen += [aus, f"Brief: {woerter(entwurf['brief'])} von {WORT_MAX} Wörtern"]
    if (ordner / "stelle.md").exists():
        meldungen.append(rendern("render-stelle.mjs", ordner / "stelle.md", ordner / "Stellenanzeige.pdf"))
    print("\n".join(meldungen))

    if mit_tracker:
        sys.path.insert(0, str(HIER))
        from tracker import Tracker, stelle_lesen

        t = Tracker()
        firma = stelle_lesen(ordner).get("firma")
        if firma and t.finden(firma) is None:
            r = t.eintragen({**stelle_lesen(ordner), "status": "Vorbereitet"})
            t.speichern()
            print(f"Tracker Zeile {r}: {firma} (Vorbereitet)")


def main(argv: list[str]) -> None:
    if not argv or argv[0].startswith("-"):
        raise SystemExit(__doc__)
    ordner = (WURZEL / argv[0]).resolve()
    if not (ordner / "entwurf.json").exists():
        raise SystemExit(f"{argv[0]}/entwurf.json fehlt")
    bauen(ordner, mit_tracker="--ohne-tracker" not in argv)


if __name__ == "__main__":
    main(sys.argv[1:])
