#!/usr/bin/env python3
"""
Stellensuche auf StepStone über Scrapling.

    tools/.venv/bin/python tools/stepstone.py [ausgabe.json]

StepStone liefert die Trefferliste serverseitig gerendert aus, deshalb reicht
der leichtgewichtige HTTP-Fetcher — kein Browser nötig. Zwischen den Abrufen
liegt eine Pause, damit die Last vertretbar bleibt.

Die Suchbegriffe, Orte und Ausschlusswörter kommen aus suchprofil.json.
"""
import json
import re
import sys
import time
from pathlib import Path

from scrapling.fetchers import Fetcher

HIER = Path(__file__).parent
PROFIL = json.loads((HIER / "suchprofil.json").read_text(encoding="utf-8"))
PAUSE = 1.5          # Sekunden zwischen Abrufen
SEITEN = 2           # Seiten je Suchkombination (25 Treffer pro Seite)


def slug(text: str) -> str:
    t = text.lower()
    for a, b in [("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")]:
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def ausgeschlossen(text: str) -> bool:
    t = text.lower()
    for wort in PROFIL["ausschluss"]:
        w = wort.lower()
        i = t.find(w)
        if i == -1:
            continue
        davor = " " if i == 0 else t[i - 1]
        danach = " " if i + len(w) >= len(t) else t[i + len(w)]
        if not re.match(r"[a-zäöüß0-9]", davor) and not re.match(r"[a-zäöüß0-9]", danach):
            return True
    return False


def seite_lesen(url: str) -> list[dict]:
    seite = Fetcher.get(url, timeout=30)
    if seite.status != 200:
        raise RuntimeError(f"HTTP {seite.status}")
    titel = seite.css('[data-at="job-item-title"]')
    firmen = seite.css('[data-at="job-item-company-name"]')
    orte = seite.css('[data-at="job-item-location"]')
    alter = seite.css('[data-at="job-item-timeago"]')

    treffer = []
    for i, t in enumerate(titel):
        href = t.attrib.get("href") or ""
        if not href:
            link = t.find_ancestor(lambda e: e.tag == "a")
            href = link.attrib.get("href", "") if link else ""
        if href.startswith("/"):
            href = "https://www.stepstone.de" + href
        hole = lambda liste, j: liste[j].get_all_text().strip() if j < len(liste) else ""
        treffer.append({
            "quelle": "StepStone",
            "titel": t.get_all_text().strip(),
            "firma": hole(firmen, i),
            "ort": hole(orte, i),
            "alter": hole(alter, i),
            "url": href.split("?")[0],
        })
    return treffer


def main() -> None:
    gefunden: dict[str, dict] = {}
    fehler: list[str] = []
    orte = [slug(o) for o in PROFIL["orte"]] + [None]   # None = bundesweit

    for begriff in PROFIL["suchbegriffe"]:
        s = slug(begriff)
        for ort in orte:
            basis = f"https://www.stepstone.de/jobs/{s}"
            if ort:
                basis += f"/in-{ort}"
            for seite in range(1, SEITEN + 1):
                url = basis if seite == 1 else f"{basis}?page={seite}"
                try:
                    for job in seite_lesen(url):
                        if not job["titel"] or ausgeschlossen(f'{job["titel"]} {job["firma"]}'):
                            continue
                        job["suchbegriff"] = begriff
                        gefunden.setdefault(job["url"], job)
                except Exception as e:                       # noqa: BLE001
                    fehler.append(f"{begriff} @ {ort or 'bundesweit'} S.{seite}: {e}")
                time.sleep(PAUSE)
        print(f"  {begriff:24s} → {len(gefunden)} kumuliert", flush=True)

    ergebnis = {
        "quelle": "StepStone",
        "gesucht_am": time.strftime("%Y-%m-%d"),
        "anzahl": len(gefunden),
        "fehler": fehler,
        "treffer": sorted(gefunden.values(), key=lambda j: (j["firma"], j["titel"])),
    }
    ziel = Path(sys.argv[1]) if len(sys.argv) > 1 else HIER.parent / "stellen" / "_stepstone.json"
    ziel.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(gefunden)} Treffer → {ziel}")
    if fehler:
        print(f"{len(fehler)} Fehler, erste drei:\n  " + "\n  ".join(fehler[:3]))


if __name__ == "__main__":
    main()
