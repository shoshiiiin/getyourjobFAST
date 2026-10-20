#!/usr/bin/env python3
"""
ATS-Abgleich: Welche Begriffe der Anzeige stehen in deinen Unterlagen?

    tools/.venv/bin/python tools/ats.py stellen/<ordner> [--alle]

Bewerbungen laufen bei vielen Firmen zuerst durch ein Applicant Tracking
System, das auf die Begriffe der Anzeige hin abgleicht. Dieses Werkzeug zeigt,
welche davon in deinem Anschreiben und Lebenslauf vorkommen — und teilt die
fehlenden in zwei Gruppen:

  * **belegte Lücke** — der Begriff fehlt, obwohl profil/belege.md oder
    profil/master-cv.md ihn decken. Hier lohnt eine Änderung.
  * **nicht belegt** — der Begriff fehlt, weil du ihn nicht belegen kannst.
    Er bleibt draußen. Das ist kein Mangel, sondern die Regel des Projekts.

Das Werkzeug schlägt deshalb nie vor, einen Begriff einzubauen, den die Belege
nicht tragen. Keyword-Stuffing ist ausdrücklich nicht das Ziel.

Which of the posting's terms appear in your documents. Missing ones are split
into "covered by your evidence" (worth fixing) and "not covered" (correctly
absent) — it never suggests adding a term your evidence does not support.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
MIN_STAMM = 6          # so viele Anfangszeichen müssen übereinstimmen
TOP = 30               # so viele Begriffe zeigt der Bericht je Gruppe

# Füllwörter und Anzeigen-Floskeln. Großgeschrieben, weil die Erkennung auf
# deutschen Substantiven beruht und Satzanfänge sonst durchrutschen.
STOPP = {
    # Allgemein
    "aber", "alle", "allen", "aller", "als", "also", "auch", "auf", "aus", "bei", "beim",
    "bis", "dabei", "damit", "dann", "das", "dass", "dein", "deine", "deinem", "deinen",
    "deiner", "dem", "den", "der", "des", "dich", "die", "dir", "doch", "dort", "du",
    "durch", "ein", "eine", "einem", "einen", "einer", "eines", "er", "es", "etwa",
    "euch", "euer", "eure", "für", "ganz", "gern", "gerne", "haben", "hast", "hat",
    "hier", "ihr", "ihre", "ihrem", "ihren", "ihrer", "im", "in", "ins", "ist", "ja",
    "jede", "jeden", "jeder", "kann", "kannst", "mehr", "mit", "nach", "nicht", "noch",
    "nur", "ob", "oder", "ohne", "schon", "sehr", "sein", "seine", "sich", "sie", "sind",
    "so", "sowie", "um", "und", "uns", "unser", "unsere", "unserem", "unseren", "unserer",
    "vom", "von", "vor", "was", "wenn", "wer", "werden", "wie", "wir", "wird", "wirst",
    "zu", "zum", "zur", "über",
    # Anzeigen-Floskeln
    "arbeit", "arbeiten", "aufgabe", "aufgaben", "benefits", "bereich", "bewerbung",
    "bewerbungen", "bieten", "bringst", "chance", "einsatz", "erfahrung", "erwartet",
    "firma", "freuen", "gesucht", "gut", "gute", "guten", "haus", "jahre", "jahren",
    "job", "kollegen", "kolleginnen", "können", "mensch", "menschen", "mitarbeiter",
    "mitarbeiterinnen", "möglichkeit", "möglichkeiten", "neue", "neuen", "profil",
    "rahmen", "rolle", "stelle", "stellenanzeige", "suchen", "tag", "team", "teams",
    "unternehmen", "vorteil", "vorteile", "welt", "wichtig", "zukunft", "zusammen",
    # Englisch
    "and", "are", "the", "you", "your", "our", "with", "for", "from", "that", "this",
    "will", "have", "has", "who", "what", "work", "working", "role", "team", "company",
    "about", "join", "offer", "benefits", "requirements", "responsibilities",
    # Rechtsformen, Anreden, Zahlwörter, Benefits — tragen keine Information
    "gmbh", "ag", "kg", "ohg", "mbh", "se", "ug", "co", "inc", "ltd",
    "frau", "herr", "herrn", "dr", "prof", "dipl",
    "ein", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn",
    "urlaubstage", "urlaub", "weiterbildungsbudget", "gehalt", "vergütung",
    "homeoffice", "idee", "plus", "tage", "tagen", "stunden", "woche", "wochen",
}

# Abkürzungen dürfen kurz sein; sie tragen oft das meiste Gewicht.
ABKUERZUNG = re.compile(r"^[A-ZÄÖÜ][A-ZÄÖÜ0-9.+#/-]{1,7}$")
WORT = re.compile(r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß0-9.+#&/-]*")


def _kandidat(wort: str) -> bool:
    """Taugt das Wort als Schlagwort? Substantive, Abkürzungen, Fachbegriffe."""
    if wort.lower() in STOPP or len(wort) < 3:
        return False
    if ABKUERZUNG.match(wort):
        return True
    return wort[0].isupper() and len(wort) >= 4


# Zwei verschiedene Grenzen, die man nicht verwechseln darf:
#   SATZ_TRENNER  — hier endet ein Satz. Danach steht oft ein großgeschriebenes
#                   Adjektiv („Abgeschlossenes Studium“), das kein Schlagwort ist.
#   PAAR_TRENNER  — hier endet ein Gedanke, Komma eingeschlossen. Über diese
#                   Grenze hinweg entsteht kein Zweiwortpaar.
# Früher war beides dasselbe Zeichen-Set, und das Komma hat dadurch jedes
# Listenelement zum „Satzanfang“ gemacht — der Adjektivfilter fraß dann
# gültige Schlagworte wie „Rollout“ in „BPMN, Rollout und SAP“.
SATZ_TRENNER = ".!?:;"
PAAR_TRENNER = SATZ_TRENNER + ","
WORT_MIT_ZEICHEN = re.compile(rf"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß0-9.+#&/-]*[{re.escape(PAAR_TRENNER)}]?")


def _zerlegen(zeile: str) -> list[tuple[str, bool, bool]]:
    """Je Wort: (Wort, steht am Satzanfang, davor endete ein Gedanke)."""
    aus: list[tuple[str, bool, bool]] = []
    satzanfang, gedankenbruch = True, True
    for roh in WORT_MIT_ZEICHEN.findall(zeile):
        sauber = roh.strip(PAAR_TRENNER + "()[]{}\"'/-")
        if sauber:
            aus.append((sauber, satzanfang, gedankenbruch))
        letztes = roh[-1]
        satzanfang = letztes in SATZ_TRENNER
        gedankenbruch = letztes in PAAR_TRENNER
    return aus


def begriffe(text: str, kandidaten: bool = False) -> Counter:
    """
    Schlagworte eines Textes mit Häufigkeit, inklusive Zweiwortpaaren.

    Zweiwortpaare entstehen nie über eine Satz- oder Kommagrenze hinweg.

    `kandidaten=True` schaltet zusätzlich einen Filter ein: ein
    großgeschriebenes Wort, das *nur* am Satzanfang und höchstens zweimal
    vorkommt, fällt weg — das sind fast immer Adjektive („Abgeschlossenes“,
    „Mehrjährige“). Dieser Filter gehört **nur auf den Anzeigentext**. Auf die
    Unterlagen angewandt würde er Bullets köpfen, die zulässig mit einem
    Substantiv beginnen („Leitung der Einführung …“), und die Begriffe
    fälschlich als fehlend melden.
    """
    gefunden: Counter = Counter()
    nur_am_anfang: dict[str, bool] = {}
    for zeile in (text or "").splitlines():
        gewicht = 2 if zeile.lstrip().startswith(("-", "*", "•")) else 1
        worte = _zerlegen(zeile)
        for i, (w, am_satzanfang, _) in enumerate(worte):
            if not _kandidat(w):
                continue
            gefunden[w] += gewicht
            nur_am_anfang[w] = nur_am_anfang.get(w, True) and am_satzanfang
            if i + 1 < len(worte):
                folge, _, neuer_gedanke = worte[i + 1]
                if not neuer_gedanke and _kandidat(folge):
                    paar = f"{w} {folge}"
                    gefunden[paar] += gewicht
                    nur_am_anfang[paar] = nur_am_anfang.get(paar, True) and am_satzanfang
    if kandidaten:
        for wort, allein_am_anfang in nur_am_anfang.items():
            if allein_am_anfang and gefunden[wort] <= 2 and not ABKUERZUNG.match(wort.split()[0]):
                del gefunden[wort]
    return gefunden


def stamm(wort: str) -> str:
    return re.sub(r"[^a-zäöüß0-9]", "", wort.lower())


# Deutsche Beugungsendungen. Nur wenn der Rest hinter dem gemeinsamen Stamm
# genau so aussieht, gelten zwei Wörter als dasselbe. Das trennt „Prozesse“ /
# „Prozessen“ (Rest „n“) sauber von „Projekt“ / „Projektion“ (Rest „ion“).
ENDUNGEN = frozenset({"", "e", "en", "er", "ern", "es", "s", "n", "em", "in", "innen"})


def passt(a: str, b: str) -> bool:
    """Zwei Begriffe meinen dasselbe — gleicher Stamm, nur andere Beugung."""
    sa, sb = stamm(a), stamm(b)
    if not sa or not sb:
        return False
    if sa == sb:
        return True
    kurz, lang = (sa, sb) if len(sa) <= len(sb) else (sb, sa)
    if len(kurz) < MIN_STAMM or not lang.startswith(kurz):
        return False
    return lang[len(kurz):] in ENDUNGEN


def steckt_drin(begriff: str, heuhaufen: set[str]) -> bool:
    return any(passt(begriff, h) for h in heuhaufen)


@dataclass(frozen=True)
class Abgleich:
    """Ergebnis: drin, belegte Lücke, nicht belegt."""
    drin: list[tuple[str, int]]
    luecke: list[tuple[str, int]]
    ungedeckt: list[tuple[str, int]]

    @property
    def geprueft(self) -> int:
        return len(self.drin) + len(self.luecke) + len(self.ungedeckt)

    @property
    def abdeckung(self) -> float:
        return 100.0 * len(self.drin) / self.geprueft if self.geprueft else 0.0


def abgleichen(anzeige: str, unterlagen: str, belege: str, mindest: int = 1) -> Abgleich:
    """Vergleicht die Schlagworte der Anzeige mit Unterlagen und Belegen."""
    u = set(begriffe(unterlagen))
    b = set(begriffe(belege))
    drin: list[tuple[str, int]] = []
    luecke: list[tuple[str, int]] = []
    ungedeckt: list[tuple[str, int]] = []
    for wort, n in begriffe(anzeige, kandidaten=True).most_common():
        if n < mindest:
            continue
        ziel = drin if steckt_drin(wort, u) else (luecke if steckt_drin(wort, b) else ungedeckt)
        ziel.append((wort, n))
    return Abgleich(drin, luecke, ungedeckt)


# --- Dateien einlesen -----------------------------------------------------

def anzeigentext(ordner: Path) -> str:
    """Der Volltext aus stelle.md, ohne die Kopftabelle."""
    datei = ordner / "stelle.md"
    if not datei.exists():
        raise SystemExit(f"{datei.relative_to(WURZEL)} fehlt — ohne Anzeige kein Abgleich.")
    text = datei.read_text(encoding="utf-8")
    teile = re.split(r"^## .*Volltext.*$", text, maxsplit=1, flags=re.M)
    return teile[1] if len(teile) > 1 else text


def unterlagentext(ordner: Path) -> str:
    """
    Alles, was in den Dokumenten dieser Bewerbung steht.

    Nach dem Bau liegen anschreiben.json und lebenslauf.json im Ordner — dann
    ist es einfach. Vorher gibt es nur entwurf.json, und dort stehen die
    Lebenslauf-Bullets bloß als Indizes. In dem Fall setzen wir den Lebenslauf
    aus dem Entwurf und profil/lebenslauf-allgemein.json zusammen, sonst
    gälten alle Bullets als fehlend.
    """
    stuecke: list[str] = []
    for name in ("anschreiben.json", "lebenslauf.json"):
        datei = ordner / name
        if datei.exists():
            stuecke.append(_flach(json.loads(datei.read_text(encoding="utf-8"))))

    entwurf_datei = ordner / "entwurf.json"
    if not stuecke and entwurf_datei.exists():
        entwurf = json.loads(entwurf_datei.read_text(encoding="utf-8"))
        stuecke.append(_flach(entwurf))
        stuecke.append(_lebenslauf_aus_entwurf(entwurf))

    if not stuecke:
        raise SystemExit("Weder gebaute Unterlagen noch entwurf.json gefunden.")
    return "\n".join(s for s in stuecke if s)


def _lebenslauf_aus_entwurf(entwurf: dict) -> str:
    """Den zugeschnittenen Lebenslauf im Kopf bauen, ohne PDFs zu rendern."""
    wahl = entwurf.get("lebenslauf")
    if not wahl:
        return ""
    englisch = entwurf.get("sprache") == "en"
    basis_datei = WURZEL / "profil" / ("lebenslauf-allgemein-en.json" if englisch
                                       else "lebenslauf-allgemein.json")
    if not basis_datei.exists():
        return ""
    sys.path.insert(0, str(WURZEL / "tools"))
    try:
        from bewerbung import lebenslauf  # noqa: PLC0415
    except Exception:
        return ""
    basis = json.loads(basis_datei.read_text(encoding="utf-8"))
    try:
        return _flach(lebenslauf(basis, wahl))
    except (KeyError, IndexError, TypeError):
        return ""


def belegtext() -> str:
    """Alles, was du behaupten darfst."""
    stuecke: list[str] = []
    for name in ("belege.md", "master-cv.md", "lebenslauf-allgemein.json"):
        datei = WURZEL / "profil" / name
        if datei.exists():
            roh = datei.read_text(encoding="utf-8")
            stuecke.append(_flach(json.loads(roh)) if name.endswith(".json") else roh)
    return "\n".join(stuecke)


def _flach(daten) -> str:
    """Alle Zeichenketten einer JSON-Struktur, eine je Zeile."""
    if isinstance(daten, str):
        return daten
    if isinstance(daten, dict):
        return "\n".join(_flach(v) for k, v in daten.items() if not k.startswith("_"))
    if isinstance(daten, list):
        return "\n".join(_flach(v) for v in daten)
    return ""


# --- Bericht --------------------------------------------------------------

def _liste(paare: list[tuple[str, int]], grenze: int) -> str:
    sichtbar = paare[:grenze]
    rest = len(paare) - len(sichtbar)
    text = " · ".join(f"{w} {n}×" for w, n in sichtbar)
    return text + (f" … und {rest} weitere" if rest > 0 else "")


def bericht(a: Abgleich, alle: bool = False) -> str:
    grenze = 10**6 if alle else TOP
    zeilen = [
        f"Abdeckung: {len(a.drin)} von {a.geprueft} Begriffen der Anzeige ({a.abdeckung:.0f} %)",
        "",
        f"IN DEINEN UNTERLAGEN ({len(a.drin)})",
        "  " + (_liste(a.drin, grenze) or "—"),
        "",
        f"FEHLT, OBWOHL BELEGT ({len(a.luecke)})  ← hier lohnt eine Änderung",
        "  " + (_liste(a.luecke, grenze) or "—"),
        "",
        f"FEHLT UND IST NICHT BELEGT ({len(a.ungedeckt)})  ← bleibt draußen",
        "  " + (_liste(a.ungedeckt, grenze) or "—"),
    ]
    if a.luecke:
        zeilen += ["", "Die mittlere Gruppe deckt deine Belege ab — diese Begriffe darfst du",
                   "einbauen. Die untere nicht: Was nicht belegt ist, kommt nicht hinein."]
    return "\n".join(zeilen)


def kurzfassung(a: Abgleich) -> str:
    """Eine Zeile für die Ausgabe von bewerbung.py."""
    hinweis = f", {len(a.luecke)} belegte Lücke(n)" if a.luecke else ""
    return f"ATS: {a.abdeckung:.0f} % der Anzeigenbegriffe in den Unterlagen{hinweis}"


def fuer_ordner(ordner: Path, mindest: int = 1) -> Abgleich:
    return abgleichen(anzeigentext(ordner), unterlagentext(ordner), belegtext(), mindest)


def main(argv: list[str]) -> None:
    if not argv or argv[0].startswith("-"):
        raise SystemExit(__doc__)
    ordner = (WURZEL / argv[0]).resolve()
    if not ordner.is_dir():
        raise SystemExit(f"{argv[0]} ist kein Ordner")
    print(bericht(fuer_ordner(ordner), alle="--alle" in argv))


if __name__ == "__main__":
    main(sys.argv[1:])
