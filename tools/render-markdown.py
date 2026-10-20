#!/usr/bin/env python3
"""
Rendert ein Markdown-Dokument als lesbares A4-PDF.

    python3 tools/render-markdown.py <datei.md> [ausgabe.pdf]
    python3 tools/render-markdown.py <datei.md> --html   # nur HTML, kein PDF

Gedacht für Arbeitsdokumente — Gesprächsvorbereitungen, Analysen, Notizen —
nicht für Bewerbungsdokumente. Lebenslauf und Anschreiben laufen weiter über
die jsPDF-Renderer (render-cv.mjs, render-anschreiben.mjs), weil dort das
Layout pixelgenau festliegt.

Der Weg ist Markdown -> HTML -> Headless Chrome. Bewusst ohne Abhängigkeiten:
Der Konverter deckt genau die Konstrukte ab, die in diesen Dokumenten
vorkommen (Überschriften, Tabellen, Zitate, Listen, fett/kursiv/Code, Links),
und Chrome ist auf dem Rechner ohnehin installiert.
"""
import html
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# Chrome rendert das PDF. Reihenfolge = Vorzug.
BROWSER = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
]
DRUCK_TIMEOUT_S = 120


# --------------------------------------------------------------------------
# Inline-Auszeichnung
# --------------------------------------------------------------------------

def inline(text):
    """Wandelt fett, kursiv, Code und Links innerhalb einer Zeile um."""
    out = html.escape(text, quote=False)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", out)
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', out)
    return out


# --------------------------------------------------------------------------
# Blockparser — jeder liefert (html, naechster_index) oder None
# --------------------------------------------------------------------------

def _trennlinie(zeilen, i):
    if not re.fullmatch(r"\s*---+\s*", zeilen[i]):
        return None
    return "<hr>", i + 1


def _ueberschrift(zeilen, i):
    m = re.match(r"^(#{1,6})\s+(.*)$", zeilen[i])
    if not m:
        return None
    n = len(m.group(1))
    return f"<h{n}>{inline(m.group(2).strip())}</h{n}>", i + 1


def _zellen(zeile):
    return [c.strip() for c in zeile.strip().strip("|").split("|")]


def _tabelle(zeilen, i):
    ist_tabelle = (
        zeilen[i].lstrip().startswith("|")
        and i + 1 < len(zeilen)
        and re.match(r"^\s*\|[\s:|-]+\|\s*$", zeilen[i + 1])
    )
    if not ist_tabelle:
        return None

    kopf = _zellen(zeilen[i])
    j = i + 2
    koerper = []
    while j < len(zeilen) and zeilen[j].lstrip().startswith("|"):
        koerper.append(_zellen(zeilen[j]))
        j += 1

    # Tabellen ohne Spaltenüberschriften werden als reines Raster gesetzt.
    hat_kopf = any(c for c in kopf)
    thead = ""
    if hat_kopf:
        th = "".join(f"<th>{inline(c)}</th>" for c in kopf)
        thead = f"<thead><tr>{th}</tr></thead>"
    trs = "".join(
        "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>"
        for r in koerper
    )
    return f"<table>{thead}<tbody>{trs}</tbody></table>", j


def _absaetze_aus(block):
    """Fasst Zeilen zu Absätzen zusammen, Leerzeile trennt."""
    absaetze, puffer = [], []
    for zeile in block:
        if zeile.strip():
            puffer.append(zeile.strip())
        elif puffer:
            absaetze.append(" ".join(puffer))
            puffer = []
    if puffer:
        absaetze.append(" ".join(puffer))
    return absaetze


def _zitat(zeilen, i):
    if not zeilen[i].lstrip().startswith(">"):
        return None
    j, block = i, []
    while j < len(zeilen) and zeilen[j].lstrip().startswith(">"):
        block.append(re.sub(r"^\s*>\s?", "", zeilen[j]))
        j += 1
    inner = "".join(f"<p>{inline(a)}</p>" for a in _absaetze_aus(block))
    return f"<blockquote>{inner}</blockquote>", j


PUNKT = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")


def _liste(zeilen, i):
    m = PUNKT.match(zeilen[i])
    if not m:
        return None
    geordnet = bool(re.match(r"\d+\.", m.group(2)))

    j, punkte = i, []
    while j < len(zeilen):
        mm = PUNKT.match(zeilen[j])
        if not mm:
            # Eingerückte Folgezeile gehört zum vorherigen Punkt.
            if punkte and zeilen[j].startswith("  ") and zeilen[j].strip():
                punkte[-1] += " " + zeilen[j].strip()
                j += 1
                continue
            break
        if bool(re.match(r"\d+\.", mm.group(2))) != geordnet:
            break
        punkte.append(mm.group(3).strip())
        j += 1

    tag = "ol" if geordnet else "ul"
    lis = "".join(f"<li>{inline(p)}</li>" for p in punkte)
    return f"<{tag}>{lis}</{tag}>", j


PARSER = (_trennlinie, _ueberschrift, _tabelle, _zitat, _liste)
BLOCKANFANG = re.compile(r"^\s*(#{1,6}\s|>|[-*]\s|\d+\.\s|\||---+\s*$)")


def _absatz(zeilen, i):
    """Fallback: alles bis zur nächsten Leerzeile oder zum nächsten Block."""
    j, puffer = i, []
    while j < len(zeilen) and zeilen[j].strip() and not BLOCKANFANG.match(zeilen[j]):
        puffer.append(zeilen[j].strip())
        j += 1
    if not puffer:
        return None, i + 1
    return f"<p>{inline(' '.join(puffer))}</p>", j


def konvertiere(md):
    """Markdown -> HTML-Fragment."""
    zeilen = md.split("\n")
    raus, i = [], 0
    while i < len(zeilen):
        if not zeilen[i].strip():
            i += 1
            continue
        for parser in PARSER:
            treffer = parser(zeilen, i)
            if treffer:
                stueck, i = treffer
                raus.append(stueck)
                break
        else:
            stueck, i = _absatz(zeilen, i)
            if stueck:
                raus.append(stueck)
    return "\n".join(raus)


# --------------------------------------------------------------------------
# Seitenvorlage
# --------------------------------------------------------------------------

VORLAGE = """<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8"><title>__TITEL__</title>
<style>
@page { size: A4; margin: 18mm 16mm 16mm 16mm; }
* { box-sizing: border-box; }
body { font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
  font-size: 10.2pt; line-height: 1.55; color: #16161a; margin: 0; }
h1 { font-size: 21pt; line-height: 1.2; margin: 0 0 2mm; letter-spacing: -0.4px;
  border-bottom: 2.5pt solid #7d86d6; padding-bottom: 3mm; }
h2 { font-size: 13.5pt; margin: 9mm 0 3mm; letter-spacing: -0.2px;
  padding-top: 2.5mm; border-top: 0.6pt solid #d3d6e6; break-after: avoid; }
h3 { font-size: 11pt; margin: 6mm 0 2mm; color: #3b3f66; break-after: avoid; }
h1 + p, h2 + p, h3 + p, h2 + table, h3 + table, h2 + blockquote { break-before: avoid; }
p { margin: 0 0 2.6mm; }
strong { font-weight: 650; }
a { color: #4a52a8; text-decoration: none; }
code { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 9pt;
  background: #eef0f8; padding: 0.5mm 1.2mm; border-radius: 1.5pt; }
hr { border: 0; border-top: 0.6pt solid #d3d6e6; margin: 6mm 0; }
ul, ol { margin: 0 0 3mm; padding-left: 6mm; }
li { margin-bottom: 1.4mm; }
blockquote { margin: 3mm 0 4mm; padding: 2.6mm 4mm; background: #f4f5fb;
  border-left: 2.5pt solid #7d86d6; break-inside: avoid; }
blockquote p { margin: 0 0 1.8mm; }
blockquote p:last-child { margin-bottom: 0; }
table { width: 100%; border-collapse: collapse; margin: 2mm 0 4mm;
  font-size: 9.3pt; break-inside: avoid; }
th { text-align: left; background: #e9ebf6; font-weight: 650; font-size: 8.8pt;
  letter-spacing: 0.2px; padding: 1.8mm 2.2mm; border-bottom: 0.8pt solid #b9bee0; }
td { padding: 1.8mm 2.2mm; border-bottom: 0.4pt solid #dfe1ee; vertical-align: top; }
tr:last-child td { border-bottom: 0; }
</style></head><body>
__INHALT__
</body></html>
"""


def als_html(md):
    m = re.search(r"^#\s+(.*)$", md, re.M)
    titel = m.group(1).strip() if m else "Dokument"
    return (
        VORLAGE
        .replace("__TITEL__", html.escape(titel))
        .replace("__INHALT__", konvertiere(md))
    )


# --------------------------------------------------------------------------
# PDF-Druck
# --------------------------------------------------------------------------

def finde_browser():
    for pfad in BROWSER:
        if Path(pfad).exists():
            return pfad
    raise SystemExit(
        "Kein Chromium-basierter Browser gefunden. Gesucht wurde in:\n  "
        + "\n  ".join(BROWSER)
    )


def drucke(html_pfad, pdf_pfad):
    befehl = [
        finde_browser(),
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_pfad}",
        html_pfad.as_uri(),
    ]
    try:
        ergebnis = subprocess.run(
            befehl, capture_output=True, text=True, timeout=DRUCK_TIMEOUT_S
        )
    except subprocess.TimeoutExpired:
        raise SystemExit(f"Chrome hat nach {DRUCK_TIMEOUT_S} s nicht geantwortet.")

    # Chrome meldet auf macOS harmlose task_policy_set-Fehler auf stderr und
    # liefert trotzdem ein PDF. Deshalb zählt das Ergebnis, nicht der Rückgabewert.
    if not pdf_pfad.exists():
        raise SystemExit(
            f"Chrome hat kein PDF erzeugt (Code {ergebnis.returncode}).\n"
            f"{ergebnis.stderr.strip()[:800]}"
        )


# --------------------------------------------------------------------------

def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        raise SystemExit(__doc__.strip())

    quelle = Path(argv[0])
    if not quelle.is_file():
        raise SystemExit(f"Datei nicht gefunden: {quelle}")

    nur_html = "--html" in argv[1:]
    ziel_arg = next((a for a in argv[1:] if not a.startswith("--")), None)

    md = quelle.read_text(encoding="utf-8")
    seite = als_html(md)

    if nur_html:
        ziel = Path(ziel_arg) if ziel_arg else quelle.with_suffix(".html")
        ziel.write_text(seite, encoding="utf-8")
        print(f"{ziel}  ({len(seite) / 1024:.0f} KB)")
        return

    ziel = Path(ziel_arg) if ziel_arg else quelle.with_suffix(".pdf")
    with tempfile.TemporaryDirectory() as tmp:
        zwischen = Path(tmp) / "seite.html"
        zwischen.write_text(seite, encoding="utf-8")
        drucke(zwischen, ziel.resolve())

    seiten = len(re.findall(rb"/Type\s*/Page[^s]", ziel.read_bytes()))
    print(f"{ziel}  ({seiten} Seiten, {ziel.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main(sys.argv[1:])
