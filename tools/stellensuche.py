#!/usr/bin/env python3
"""
Automatische Stellensuche nach profil/suchmandat.json.

    tools/.venv/bin/python tools/stellensuche.py [--tage 3] [--begriffe 5] [--ohne-meldung]

Quellen: StepStone im Umkreis des eigenen Orts, LinkedIn lokal und LinkedIn
remote (Deutschland). Danach: Titel nach Mandat, Tracker-Firmen und
Personaldienstleister raus, schon gesehene Anzeigen raus, Entfernung zum
eigenen Ort, Volltext für die Übrigen, Einordnung remote / lokal / offen.

Ort und Suchradius stehen in profil/person.json.

Schreibt stellen/suchlaeufe/JJJJ-MM-TT.json und .md und merkt sich alle
geprüften Anzeigen in stellen/suchlaeufe/gesehen.json. Ist TYPESAFE_API_KEY in
.env.local gesetzt, sortiert Jev die Treffer zusätzlich vor.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import subprocess
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parent
sys.path.insert(0, str(HIER))

from suche import bekannt, bericht, quellen  # noqa: E402
from suche.filter import HYBRID, REMOTE_VOLL, UMKREIS_KM, einordnen, schluessel, signale, titel_art  # noqa: E402
from suche.geo import Geo  # noqa: E402
import person as _person  # noqa: E402

ORT = _person.person()["ort"]
ORT_LINKEDIN = _person.person().get("ort_linkedin", f"{ORT}, Deutschland")

PROFIL = json.loads((HIER / "suchprofil.json").read_text(encoding="utf-8"))
GRUPPEN = ("remote", "lokal", "remote_portal", "offen", "raus")
logging.getLogger("scrapling").setLevel(logging.WARNING)
ZIEL = WURZEL / "stellen" / "suchlaeufe"


def log(*teile) -> None:
    print(dt.datetime.now().strftime("%H:%M:%S"), *teile, flush=True)


MAX_FEHLERQUOTE = 0.5  # mehr gescheiterte Abrufe heißt: Netz oder Portal kaputt, kein leerer Tag


def sammeln(begriffe: list[str], tage: int) -> tuple[list[dict], int, int]:
    sekunden = str(tage * 86400)
    lokal = {"location": ORT_LINKEDIN, "distance": str(int(UMKREIS_KM)), "f_TPR": f"r{sekunden}"}
    remote = {"location": "Germany", "f_WT": "2", "f_TPR": f"r{sekunden}"}
    abrufe = [
        ("StepStone", lambda b: quellen.stepstone_umkreis(b, ORT, int(UMKREIS_KM), PROFIL["stepstone_seiten"])),
        ("LinkedIn lokal", lambda b: quellen.linkedin(b, lokal, PROFIL["linkedin_seiten"], "LinkedIn lokal")),
        ("LinkedIn remote", lambda b: quellen.linkedin(b, remote, PROFIL["linkedin_seiten"], "LinkedIn remote")),
    ]
    alle, fehler = [], 0
    versuche = len(begriffe) * len(abrufe)
    for b in begriffe:
        for name, holen in abrufe:
            try:
                alle += holen(b)
            except Exception as e:  # noqa: BLE001 — ein Begriff darf den Lauf nicht beenden
                fehler += 1
                log("Fehler", name, b, e)
        log(f"{b:<28} {len(alle)} kumuliert")
    return alle, fehler, versuche


def vorfiltern(roh: list[dict], sperre: dict, gesehen: dict) -> tuple[list[dict], dict]:
    stat = {"roh": len(roh), "titel": 0, "gesperrt": 0, "gesehen": 0, "dublette": 0}
    schluessel_gesehen, bleiben = set(), []
    for j in roh:
        k = schluessel(j)
        if k in schluessel_gesehen:
            stat["dublette"] += 1
        elif not titel_art(j.get("titel", "")):
            stat["titel"] += 1
        elif bekannt.gesperrt(j.get("firma", ""), sperre):
            stat["gesperrt"] += 1
        elif j["url"] in gesehen:
            stat["gesehen"] += 1
        else:
            bleiben.append({**j, "titel_art": titel_art(j["titel"])})
        schluessel_gesehen.add(k)
    return bleiben, stat


def anreichern(jobs: list[dict], geo: Geo) -> list[dict]:
    fertig = []
    for i, j in enumerate(jobs, 1):
        job = dict(j)
        naechster = geo.naechster(job.get("ort", ""))
        job["km"], job["naechster_ort"] = naechster if naechster else (None, None)
        zu_weit = job["km"] is not None and job["km"] > UMKREIS_KM
        if zu_weit and job["quelle"] != "LinkedIn remote" and "remote" not in job.get("ort", "").lower():
            job["einordnung"] = "raus"
            fertig.append(job)
            continue
        job.update(quellen.details(job))
        job["remote_signal"] = signale(job.get("beschreibung", ""), REMOTE_VOLL)
        job["hybrid_signal"] = signale(job.get("beschreibung", ""), HYBRID)
        job["einordnung"] = einordnen(job)
        fertig.append(job)
        if i % 25 == 0:
            log(f"Details {i}/{len(jobs)}")
    return fertig


def ohne_volltext(job: dict) -> bool:
    return bool(job.get("fehler")) and not job.get("beschreibung")


def zusammenfuehren(datei: Path, neu: list[dict]) -> list[dict]:
    """Ein zweiter Lauf am selben Tag ergänzt den ersten, statt ihn zu überschreiben."""
    if not datei.exists():
        return neu
    alt = json.loads(datei.read_text(encoding="utf-8")).get("treffer", [])
    neue_urls = {j["url"] for j in neu}
    return [j for j in alt if j["url"] not in neue_urls] + neu


def jev(datei: Path) -> str:
    env = WURZEL / ".env.local"
    if not env.exists() or "TYPESAFE_API_KEY=" not in env.read_text(encoding="utf-8"):
        return "_Jev-Vorsortierung aus: `TYPESAFE_API_KEY` fehlt in `.env.local`._"
    try:
        p = subprocess.run(["node", str(HIER / "jev-vorsortieren.mjs"), str(datei)], cwd=WURZEL,
                           capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.SubprocessError) as e:
        log("Jev nicht gestartet:", e)
        return "_Jev-Vorsortierung fehlgeschlagen, siehe Log._"
    if p.returncode != 0:
        log("Jev fehlgeschlagen:", p.stderr.strip()[-300:])
        return "_Jev-Vorsortierung fehlgeschlagen, siehe Log._"
    return f"Jev-Vorsortierung: `{datei.with_suffix('').name}.jev.json`."


def melden(text: str, untertitel: str) -> None:
    """macOS-Mitteilung; Text und Untertitel stammen nur aus eigenen Zahlen und Dateinamen."""
    skript = f'display notification "{text}" with title "Stellensuche" subtitle "{untertitel}"'
    try:
        subprocess.run(["osascript", "-e", skript], check=False, timeout=15, capture_output=True)
    except (OSError, subprocess.SubprocessError) as e:
        log("Mitteilung nicht möglich:", e)


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    a.add_argument("--tage", type=int, default=3, help="Anzeigen der letzten N Tage (LinkedIn)")
    a.add_argument("--begriffe", type=int, default=0, help="nur die ersten N Suchbegriffe (zum Testen)")
    a.add_argument("--ohne-meldung", action="store_true")
    args = a.parse_args()

    heute = dt.date.today().isoformat()
    begriffe = PROFIL["suchbegriffe"][: args.begriffe or None]
    log(f"Suchlauf {heute}: {len(begriffe)} Begriffe, {args.tage} Tage")

    roh, fehler, versuche = sammeln(begriffe, args.tage)
    if fehler > versuche * MAX_FEHLERQUOTE:
        log(f"Abbruch: {fehler} von {versuche} Abrufen gescheitert — kein Bericht, nichts als gesehen gemerkt")
        if not args.ohne_meldung:
            melden(f"Suchlauf fehlgeschlagen ({fehler}/{versuche} Abrufe)", "siehe suche.log")
        sys.exit(1)
    gesehen = bekannt.gesehen_laden()
    kandidaten, stat = vorfiltern(roh, bekannt.gesperrte_firmen(), gesehen)
    stat["fehler"] = fehler
    log(f"{len(kandidaten)} Kandidaten nach Vorfilter {stat}")

    geo = Geo()
    jobs = anreichern(kandidaten, geo)
    geo.speichern()
    stat["fehler"] += sum(ohne_volltext(j) for j in jobs)

    ZIEL.mkdir(parents=True, exist_ok=True)
    datei = ZIEL / f"{heute}.json"
    treffer = zusammenfuehren(datei, [j for j in jobs if j["einordnung"] != "raus"])
    gruppen = {g: [j for j in treffer if j["einordnung"] == g] for g in GRUPPEN[:-1]}
    datei.write_text(json.dumps({"gesucht_am": heute, "statistik": stat, "treffer": treffer,
                                 "aussortiert": [{k: j.get(k) for k in ("titel", "firma", "ort", "km", "url")}
                                                 for j in jobs if j["einordnung"] == "raus"]},
                                ensure_ascii=False, indent=1), encoding="utf-8")
    hinweis = jev(datei) if treffer else ""
    md = datei.with_suffix(".md")
    md.write_text(bericht.markdown(dt.date.today().strftime("%d.%m.%Y"), gruppen, stat, hinweis), encoding="utf-8")
    # Ohne Volltext nicht merken: beim nächsten Lauf neu versuchen
    bekannt.gesehen_speichern(gesehen, [j["url"] for j in jobs if not ohne_volltext(j)])
    log("Fertig:", ", ".join(f"{len(v)} {g}" for g, v in gruppen.items()), "→", md)
    if not args.ohne_meldung:
        r, lo = len(gruppen["remote"]), len(gruppen["lokal"])
        melden(f"{r} Home-Office, {lo} nahe {ORT}" if r + lo else "Keine neuen passenden Stellen", md.name)


if __name__ == "__main__":
    main()
