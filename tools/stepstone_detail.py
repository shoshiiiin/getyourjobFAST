#!/usr/bin/env python3
"""
Holt die Detaildaten einzelner StepStone-Anzeigen.

    tools/.venv/bin/python tools/stepstone_detail.py <url> [<url> ...]
    tools/.venv/bin/python tools/stepstone_detail.py --aus stellen/_stepstone.json --max 12

StepStone bettet je Anzeige ein JSON-LD-Objekt vom Typ JobPosting ein. Das
enthält Titel, Arbeitgeber, Ort, Beschäftigungsart, Veröffentlichungs- und
Ablaufdatum sowie den vollständigen Beschreibungstext — verlässlicher als
jedes HTML-Parsing.

Abgelaufene Anzeigen (validThrough in der Vergangenheit) werden markiert.
"""
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from scrapling.fetchers import Fetcher

HIER = Path(__file__).parent
PAUSE = 1.5


def text_aus_html(html: str) -> str:
    t = re.sub(r"<(br|/p|/li|/div|/h\d)[^>]*>", "\n", html or "")
    t = re.sub(r"<[^>]+>", " ", t)
    t = (t.replace("&nbsp;", " ").replace("&amp;", "&")
          .replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'"))
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n\n", t).strip()


def jobposting(html: str) -> dict | None:
    for m in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
        try:
            d = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        kandidaten = d if isinstance(d, list) else [d]
        if isinstance(d, dict) and "@graph" in d:
            kandidaten = d["@graph"]
        for k in kandidaten:
            if isinstance(k, dict) and k.get("@type") == "JobPosting":
                return k
    return None


def abrufen(url: str) -> dict:
    seite = Fetcher.get(url, timeout=35)
    if seite.status != 200:
        return {"url": url, "fehler": f"HTTP {seite.status}"}
    jp = jobposting(seite.html_content)
    if not jp:
        return {"url": url, "fehler": "kein JobPosting im JSON-LD"}

    ort = jp.get("jobLocation") or {}
    if isinstance(ort, list):
        ort = ort[0] if ort else {}
    adresse = (ort.get("address") or {}) if isinstance(ort, dict) else {}
    gueltig = jp.get("validThrough", "")
    abgelaufen = None
    if gueltig:
        try:
            abgelaufen = datetime.fromisoformat(gueltig.replace("Z", "+00:00")) < datetime.now(timezone.utc)
        except ValueError:
            pass

    return {
        "url": url,
        "titel": jp.get("title", ""),
        "firma": (jp.get("hiringOrganization") or {}).get("name", ""),
        "ort": adresse.get("addressLocality", "") or adresse.get("streetAddress", ""),
        "plz": adresse.get("postalCode", ""),
        "land": adresse.get("addressCountry", ""),
        "art": jp.get("employmentType", ""),
        "remote": jp.get("jobLocationType", ""),
        "veroeffentlicht": (jp.get("datePosted") or "")[:10],
        "gueltig_bis": gueltig[:10],
        "abgelaufen": abgelaufen,
        "gehalt": jp.get("baseSalary"),
        "beschreibung": text_aus_html(jp.get("description", "")),
    }


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    if args[0] == "--aus":
        quelle = json.loads(Path(args[1]).read_text(encoding="utf-8"))
        grenze = int(args[args.index("--max") + 1]) if "--max" in args else 15
        urls = [t["url"] for t in quelle["treffer"]][:grenze]
    else:
        urls = args

    ergebnisse = []
    for i, url in enumerate(urls, 1):
        try:
            d = abrufen(url)
        except Exception as e:                                # noqa: BLE001
            d = {"url": url, "fehler": f"{type(e).__name__}: {e}"}
        ergebnisse.append(d)
        status = d.get("fehler") or (
            "ABGELAUFEN" if d.get("abgelaufen") else f'{d.get("veroeffentlicht","")} · {len(d.get("beschreibung",""))} Zeichen')
        print(f"  [{i}/{len(urls)}] {d.get('firma','?')[:28]:30s} {d.get('titel','?')[:44]:46s} {status}", flush=True)
        time.sleep(PAUSE)

    ziel = HIER.parent / "stellen" / "_details.json"
    ziel.write_text(json.dumps(ergebnisse, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(ergebnisse)} Anzeigen → {ziel}")


if __name__ == "__main__":
    main()
