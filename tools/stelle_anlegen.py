#!/usr/bin/env python3
"""
Legt aus einem Treffer eines Suchlaufs den Stellenordner mit stelle.md an.

    tools/.venv/bin/python tools/stelle_anlegen.py <suchbegriff> [stellen/suchlaeufe/JJJJ-MM-TT.json]

<suchbegriff> trifft Firma, Titel oder URL (ohne Groß-/Kleinschreibung). Ohne
Datei werden alle Suchläufe durchsucht, der jüngste zuerst. Fehlt der Volltext im Suchlauf, wird
die Anzeige neu abgerufen. Mehrdeutige Begriffe brechen ab und listen die Treffer.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

import person as _person

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parent
LAEUFE = WURZEL / "stellen" / "suchlaeufe"
RECHTSFORM = re.compile(r"\b(gmbh|ag|se|kg|co|mbh|ug|e\.?\s?v|ltd|inc|holding|group|deutschland|germany)\b", re.I)
GESCHLECHT = re.compile(r"\((m|w|d|f|gn|all genders?|w/m/d|m/w/d|m/f/d|d/m/w)[^)]*\)|\*in\b|:in\b", re.I)


def slug(text: str, max_woerter: int) -> str:
    t = text.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    woerter = re.findall(r"[a-z0-9]+", t)
    return "-".join(woerter[:max_woerter])


def ordnername(job: dict, tag: dt.date) -> str:
    firma = slug(RECHTSFORM.sub(" ", job.get("firma", "")), 2) or "firma"
    rolle = slug(GESCHLECHT.sub(" ", job.get("titel", "")), 4) or "stelle"
    return f"{tag.isoformat()}-{firma}-{rolle}"


def stelle_md(job: dict, tag: dt.date) -> str:
    zeilen = [
        f"# {job['titel']}", "",
        f"**{job['firma']}** · {job.get('ort', '')} · {job.get('art', '') or 'Vollzeit'}", "",
        "| | |", "|---|---|",
        f"| Quelle | {job.get('quelle', '')} |",
        f"| URL | {job['url']} |",
    ]
    if job.get("veroeffentlicht") or job.get("datum"):
        zeilen.append(f"| Veröffentlicht | {job.get('veroeffentlicht') or job.get('datum')} |")
    if job.get("gueltig_bis"):
        zeilen.append(f"| Gültig bis | {job['gueltig_bis']} |")
    if job.get("km") is not None:
        zeilen.append(f"| Entfernung {_person.person()['ort']} | {job['km']} km Luftlinie |")
    if job.get("remote_signal"):
        zeilen.append(f"| Remote im Text | {', '.join(job['remote_signal'])} |")
    zeilen += [f"| Abgerufen | {tag.isoformat()} |", "", "## Anzeige im Volltext", "", job.get("beschreibung", "").strip(), ""]
    return "\n".join(zeilen)


def passend(treffer: list[dict], begriff: str) -> list[dict]:
    b = begriff.lower()
    return [j for j in treffer if b in f"{j.get('firma', '')} {j.get('titel', '')} {j.get('url', '')}".lower()]


def finden(treffer: list[dict], begriff: str) -> dict:
    passend_ = passend(treffer, begriff)
    if len(passend_) != 1:
        liste = "\n".join(f"  - {j['firma']}: {j['titel']}" for j in passend_[:15]) or "  (keiner)"
        raise SystemExit(f"„{begriff}“ trifft {len(passend_)} Stellen:\n{liste}")
    return passend_[0]


def aus_laeufen(begriff: str, dateien: list[Path]) -> dict:
    """Jüngster Suchlauf, in dem der Begriff genau eine Stelle trifft; sonst Abbruch mit Liste."""
    for datei in sorted(dateien, reverse=True):
        treffer = json.loads(datei.read_text(encoding="utf-8"))["treffer"]
        if len(passend(treffer, begriff)) == 1:
            return finden(treffer, begriff)
    alle = [j for d in dateien for j in json.loads(d.read_text(encoding="utf-8"))["treffer"]]
    return finden(alle, begriff)


def main(argv: list[str]) -> None:
    if not argv:
        raise SystemExit(__doc__)
    dateien = [Path(argv[1])] if len(argv) > 1 else [d for d in LAEUFE.glob("20*.json") if ".jev." not in d.name]
    if not dateien:
        raise SystemExit("Noch kein Suchlauf in stellen/suchlaeufe/")
    job = aus_laeufen(argv[0], dateien)
    if not job.get("beschreibung"):
        sys.path.insert(0, str(HIER))
        from suche.quellen import details

        job = {**job, **details(job)}
    heute = dt.date.today()
    ordner = WURZEL / "stellen" / ordnername(job, heute)
    if ordner.exists():
        raise SystemExit(f"{ordner.relative_to(WURZEL)} gibt es schon")
    ordner.mkdir(parents=True)
    (ordner / "stelle.md").write_text(stelle_md(job, heute), encoding="utf-8")
    print(ordner.relative_to(WURZEL))


if __name__ == "__main__":
    main(sys.argv[1:])
