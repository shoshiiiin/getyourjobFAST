"""Markdown-Übersicht eines Suchlaufs. Rein: bekommt Daten, gibt Text zurück."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import person as _person  # noqa: E402

ORT = _person.person()["ort"]
UMKREIS = int(_person.umkreis_km())
_w = _person.person().get("wettbewerb", "").strip()
WETTBEWERB = re.compile(_w, re.I) if _w else None

STUDIUM = re.compile(r"(abgeschlossene[sn]? (Hochschul)?[Ss]tudium|Hochschulabschluss|university degree|bachelor'?s degree|master'?s degree)", re.I)
STUDIUM_ODER = re.compile(r"(oder (eine )?vergleichbare|alternativ|oder entsprechende (Berufs)?erfahrung|or equivalent)", re.I)


def hinweise(job: dict) -> str:
    text = job.get("beschreibung", "")
    h = []
    if STUDIUM.search(text) and not STUDIUM_ODER.search(text):
        h.append("Studium verlangt")
    if WETTBEWERB and WETTBEWERB.search(f"{job.get('titel', '')} {text}"):
        h.append("⚠️ Interessenkonflikt prüfen")
    if job.get("hybrid_signal") and job.get("einordnung") == "remote":
        h.append("Hybrid-Hinweis: " + ", ".join(job["hybrid_signal"][:2]))
    return " · ".join(h)


def _zelle(s: str, n: int = 60) -> str:
    s = re.sub(r"\s+", " ", str(s or "")).replace("|", "/")
    return s if len(s) <= n else s[: n - 1] + "…"


def _tabelle(jobs: list[dict], mit_km: bool) -> list[str]:
    kopf = "| km | Firma | Rolle | Ort | Hinweis |" if mit_km else "| Firma | Rolle | Signal im Text | Hinweis |"
    zeilen = [kopf, "|" + "---|" * (kopf.count("|") - 1)]
    for j in jobs:
        rolle = f"[{_zelle(j['titel'])}]({j['url']})"
        if mit_km:
            zeilen.append(f"| {j['km']:.0f} | {_zelle(j['firma'], 40)} | {rolle} | {_zelle(j['ort'], 30)} | {hinweise(j)} |")
        else:
            signal = _zelle(", ".join(j.get("remote_signal", [])), 40)
            zeilen.append(f"| {_zelle(j['firma'], 40)} | {rolle} | „{signal}“ | {hinweise(j)} |")
    return zeilen


def _liste(jobs: list[dict]) -> list[str]:
    return [f"- [{_zelle(j['titel'])}]({j['url']}) — {_zelle(j['firma'], 40)}, {_zelle(j['ort'], 40)}"
            + (f" · {hinweise(j)}" if hinweise(j) else "") for j in jobs]


def markdown(datum: str, gruppen: dict[str, list[dict]], statistik: dict, jev_hinweis: str) -> str:
    remote, portal, offen = gruppen.get("remote", []), gruppen.get("remote_portal", []), gruppen.get("offen", [])
    lokal = sorted(gruppen.get("lokal", []), key=lambda j: j["km"])
    teile = [
        f"# Suchlauf {datum}",
        "",
        f"**{len(remote) + len(lokal)} neue Stellen:** {len(remote)} ausdrücklich Home-Office, "
        f"{len(lokal)} höchstens {UMKREIS} km von {ORT} (Luftlinie). Dazu {len(portal)} laut LinkedIn remote "
        f"ohne Zusage im Text und {len(offen)} mit unklarem Ort.",
        "",
        f"Abgerufen {statistik['roh']} Anzeigen · Titel passt nicht {statistik['titel']} · "
        f"bekannte/gesperrte Firmen {statistik['gesperrt']} · schon gesehen {statistik['gesehen']} · "
        f"Fehler beim Abruf {statistik['fehler']}.",
        "",
        jev_hinweis,
        "",
        "Unterlagen: Claude im Projektordner sagen, für welche Stelle — z. B. „Bewerbung für Muster GmbH“.",
        "",
        "## A. Home-Office (im Text zugesagt)",
        "",
        *(_tabelle(remote, mit_km=False) if remote else ["Keine neue Anzeige sagt ausdrücklich „voll remote“."]),
        "",
        f"## B. Nähe {ORT} (≤ {UMKREIS} km)",
        "",
        *(_tabelle(lokal, mit_km=True) if lokal else ["Keine neue Stelle im Umkreis."]),
        "",
    ]
    if portal:
        teile += ["## C. Remote laut LinkedIn, im Text nicht zugesagt", "",
                  "Der LinkedIn-Filter taugt wenig (25.09.: nur 22 von 389 sagen es im Text). Vor einer Bewerbung nachfragen.", ""]
        teile += _liste(portal) + [""]
    if offen:
        teile += ["## D. Ort unklar", ""] + _liste(offen) + [""]
    return "\n".join(teile)
