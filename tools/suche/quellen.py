"""
Abruf der Stellenquellen. Alles Netz liegt hier, die Auswertung in filter.py.

- StepStone: Trefferseiten serverseitig gerendert, Details als JSON-LD (stepstone*.py).
- LinkedIn: Gast-Schnittstelle ohne Login (jobs-guest), wie seit 25.09.2026 erprobt.

Die Pausen zwischen den Abrufen halten die Last klein; bei HTTP 429 wird einmal
gewartet und wiederholt.
"""
from __future__ import annotations

import re
import sys
import time
import urllib.parse
from pathlib import Path

from scrapling.fetchers import Fetcher

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from stepstone import seite_lesen, slug  # noqa: E402
from stepstone_detail import abrufen as stepstone_detail  # noqa: E402

PAUSE = 1.2
LI_SUCHE = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"
LI_DETAIL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"
LI_SEITE = 25


ERLAUBT = ("stepstone.de", "linkedin.com")


def portal(url: str) -> str | None:
    """„stepstone.de“ oder „linkedin.com“, wenn die URL per https genau dorthin zeigt, sonst None."""
    teile = urllib.parse.urlsplit(url or "")
    host = (teile.hostname or "").lower()
    if teile.scheme != "https":
        return None
    return next((d for d in ERLAUBT if host == d or host.endswith("." + d)), None)


def _holen(url: str):
    seite = Fetcher.get(url, timeout=30)
    if seite.status == 429:
        time.sleep(30)
        seite = Fetcher.get(url, timeout=30)
    return seite


def stepstone_umkreis(begriff: str, ort: str, radius_km: int, seiten: int) -> list[dict]:
    treffer: list[dict] = []
    for nr in range(1, seiten + 1):
        url = f"https://www.stepstone.de/jobs/{slug(begriff)}/in-{slug(ort)}?radius={radius_km}"
        if nr > 1:
            url += f"&page={nr}"
        seite = seite_lesen(url)
        treffer += [{**j, "quelle": "StepStone", "suchbegriff": begriff} for j in seite if portal(j["url"])]
        time.sleep(PAUSE)
        if len(seite) < 20:
            break
    return treffer


def linkedin(begriff: str, parameter: dict, seiten: int, quelle: str) -> list[dict]:
    treffer: list[dict] = []
    for nr in range(seiten):
        url = LI_SUCHE + urllib.parse.urlencode({"keywords": begriff, "start": nr * LI_SEITE, **parameter})
        seite = _holen(url)
        if seite.status != 200:
            if nr == 0:
                raise RuntimeError(f"LinkedIn HTTP {seite.status}")
            break  # Seite 1 ist schon da; nicht wegwerfen
        karten = seite.css("div.base-search-card")
        for k in karten:
            link = k.css("a.base-card__full-link")
            href = link[0].attrib.get("href", "").split("?")[0] if link else ""
            if not portal(href):
                continue
            text = lambda sel: (k.css(sel)[0].get_all_text().strip() if k.css(sel) else "")  # noqa: E731
            zeit = k.css("time")
            treffer.append({
                "quelle": quelle, "suchbegriff": begriff, "url": href,
                "titel": text("h3.base-search-card__title"),
                "firma": text("h4.base-search-card__subtitle"),
                "ort": text("span.job-search-card__location"),
                "datum": zeit[0].attrib.get("datetime", "") if zeit else "",
            })
        time.sleep(PAUSE)
        if len(karten) < 10:
            break
    return treffer


def details(job: dict) -> dict:
    """Volltext und Ablaufstatus einer Anzeige. Fehler landen im Feld `fehler`."""
    ziel = portal(job.get("url", ""))
    if ziel is None:
        return {"fehler": "URL gehört zu keinem bekannten Portal, nicht abgerufen"}
    try:
        if ziel == "stepstone.de":
            d = stepstone_detail(job["url"])
            if d.get("fehler"):
                return {"fehler": d["fehler"]}
            return {"beschreibung": d.get("beschreibung", ""), "abgelaufen": d.get("abgelaufen"),
                    "gueltig_bis": d.get("gueltig_bis", ""), "veroeffentlicht": d.get("veroeffentlicht", "")}
        m = re.search(r"-(\d{8,})$", job["url"].rstrip("/"))
        if not m:
            return {"fehler": "keine LinkedIn-ID in der URL"}
        seite = _holen(LI_DETAIL.format(m.group(1)))
        if seite.status != 200:
            return {"fehler": f"HTTP {seite.status}"}
        block = seite.css("div.show-more-less-html__markup")
        return {"beschreibung": block[0].get_all_text(separator="\n").strip() if block else "",
                "abgelaufen": bool(seite.css("figure.closed-job"))}
    except Exception as e:  # noqa: BLE001 — eine kaputte Anzeige darf den Lauf nicht beenden
        return {"fehler": f"{type(e).__name__}: {e}"}
    finally:
        time.sleep(PAUSE)
