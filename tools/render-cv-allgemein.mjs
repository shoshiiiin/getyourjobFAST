#!/usr/bin/env node
/**
 * Renderer für die Vorlage "Allgemeiner Lebenslauf".
 *
 *   node render-cv-allgemein.mjs <daten.json> <ausgabe.pdf>
 *
 * Geometrie 1:1 aus dem Original-PDF rekonstruiert (Vektorpfade via
 * pdftocairo, Textpositionen via pdftotext -bbox). Masse in mm.
 *
 * Aufbau je Seite: Hintergrund → Foto → Kopf → Sidebar → rechte Spalte.
 * Die rechte Spalte fliesst und bricht automatisch um; Kopf und Sidebar
 * wiederholen sich auf jeder Seite, genau wie im Original.
 */

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { laengsteKontaktzeile } from "./person.mjs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { loadPhoto } from "./design.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const { jsPDF } = await import("jspdf");

// --- Farben und Geometrie (aus dem Original vermessen) --------------------
const BG = [250, 250, 250];
const PERI = [198, 204, 255];
const INK = [17, 17, 17];

const PAGE_W = 210, PAGE_H = 297;
const BAND_W = 68.66;
const ARCS_TOP = { r: 56.23, cy: 54.14, cx: [68.66, 124.9], side: "right" };
const ARCS_BOT = { r: 85.1, cy: 212.9, cx: [153.81, 219.36], side: "left" };
const PHOTO = { xl: 4.71, xr: 79.23, ytl: 38.21, ytr: 9.93, ybl: 93.39, ybr: 65.08 };

const LEFT_X = 11.5, LEFT_W = 50;
const RIGHT_X = 81.3, RIGHT_W = 117.7;
const NAME_BASE = [31.1, 49.9];
const CONTACT_BASE = 60.0, CONTACT_GAP = 8.7;
const CONTENT_TOP = 98.3;      // Grundlinie der ersten Überschrift rechts
const SIDEBAR_TOP = 123.5;     // Grundlinie "PERSÖNLICHE DATEN"
const BOTTOM = 284;

const K = 0.5522847498;

// Im Original steckt Agrandir (kommerzielle Canva-Schrift, nicht im System).
// Ersatz: Arial Black für Name und Überschriften — die nächstliegende schwere
// Grotesk, die macOS als eigenständige TTF mitbringt. Fließtext bleibt
// Helvetica (jsPDF-Standard).
const DISPLAY_TTF = "/System/Library/Fonts/Supplemental/Arial Black.ttf";
const DISPLAY = "ArialBlack";

// Zielbreiten in mm, aus dem Original per pdftotext -bbox gemessen.
// Daraus werden die Schriftgrößen abgeleitet statt geschätzt.
const W_NAME = 99.1;        // längste Namenszeile
const W_HEADING = 64.2;     // "KERNKOMPETENZEN"
const W_CONTACT = 74.0;     // längste Kontaktzeile

function installDisplayFont(doc) {
  try {
    const b64 = readFileSync(DISPLAY_TTF).toString("base64");
    doc.addFileToVFS("ArialBlack.ttf", b64);
    doc.addFont("ArialBlack.ttf", DISPLAY, "normal");
    return true;
  } catch {
    return false;   // Fallback: Helvetica-Bold
  }
}

// --- Zeichen-Helfer -------------------------------------------------------

function halfDisc(doc, cx, cy, r, side) {
  const s = side === "right" ? 1 : -1;
  const k = K * r;
  doc.lines(
    [
      [s * k, 0, s * r, r - k, s * r, r],
      [0, k, -s * (r - k), r, -s * r, r],
    ],
    cx, cy - r, [1, 1], "F", true,
  );
}

function background(doc) {
  doc.setFillColor(...BG);
  doc.rect(0, 0, PAGE_W, PAGE_H, "F");
  doc.setFillColor(...PERI);
  for (const cx of ARCS_TOP.cx) halfDisc(doc, cx, ARCS_TOP.cy, ARCS_TOP.r, ARCS_TOP.side);
  for (const cx of ARCS_BOT.cx) halfDisc(doc, cx, ARCS_BOT.cy, ARCS_BOT.r, ARCS_BOT.side);
  doc.rect(0, 0, BAND_W, PAGE_H, "F");
}

function photo(doc, dataUrl) {
  if (!dataUrl) return;
  doc.saveGraphicsState();
  doc.moveTo(PHOTO.xr, PHOTO.ybr);
  doc.lineTo(PHOTO.xl, PHOTO.ybl);
  doc.lineTo(PHOTO.xl, PHOTO.ytl);
  doc.lineTo(PHOTO.xr, PHOTO.ytr);
  doc.close();
  doc.clip();
  doc.discardPath();
  // Bild deckt das gesamte Parallelogramm ab; der Clip schneidet zu.
  const w = PHOTO.xr - PHOTO.xl;
  const h = w * (900 / 675);           // Seitenverhältnis des Fotos
  doc.addImage(dataUrl, "JPEG", PHOTO.xl, 8.0, w, h);
  doc.restoreGraphicsState();
}

/**
 * Schriftgröße so wählen, dass `text` genau `target` mm breit wird.
 * Misst exakt den String, der später gezeichnet wird — inklusive Versalien,
 * die deutlich breiter laufen als Gemischtschreibung.
 */
function fitSize(doc, text, target, font, style = "normal", max = 80) {
  doc.setFont(font, style);
  doc.setFontSize(10);
  const per = doc.getTextWidth(text) / 10;
  return Math.min(max, target / per);
}

function header(doc, d) {
  doc.setTextColor(...INK);
  const [l1, l2] = d.nameLines.map((t) => t.toUpperCase());
  const longest = doc.getTextWidth ? (l1.length >= l2.length ? l1 : l2) : l1;
  const size = fitSize(doc, longest, W_NAME, FONT.display, FONT.displayStyle);
  doc.setFont(FONT.display, FONT.displayStyle);
  doc.setFontSize(size);
  doc.text(l1, RIGHT_X, NAME_BASE[0]);
  doc.text(l2, RIGHT_X, NAME_BASE[1]);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(fitSize(doc, laengsteKontaktzeile(d.kontakt), W_CONTACT, "helvetica"));
  let y = CONTACT_BASE;
  for (const row of d.kontakt) {
    if (Array.isArray(row)) {
      doc.text(row[0].toUpperCase(), RIGHT_X, y);
      doc.text(row[1].toUpperCase(), RIGHT_X + 43.7, y);
    } else {
      doc.text(row.toUpperCase(), RIGHT_X, y);
    }
    y += CONTACT_GAP;
  }
}

let HEADING_SIZE = null;
function heading(doc, text, x, y) {
  if (HEADING_SIZE === null) {
    HEADING_SIZE = fitSize(doc, "KERNKOMPETENZEN", W_HEADING, FONT.display, FONT.displayStyle);
  }
  doc.setFont(FONT.display, FONT.displayStyle);
  doc.setFontSize(HEADING_SIZE);
  doc.setTextColor(...INK);
  doc.text(text.toUpperCase(), x, y);
}

function sidebar(doc, d, L) {
  let y = SIDEBAR_TOP;
  heading(doc, L.persoenlichA, LEFT_X, y);
  y += 6.8;
  heading(doc, L.persoenlichB, LEFT_X, y);
  y += 12.6;

  for (const [label, value] of Object.entries(d.persoenlich)) {
    doc.setFont("helvetica", "bold");
    doc.setFontSize(12.5);
    doc.text(`${label.toUpperCase()}:`, LEFT_X, y);
    y += 6.2;
    doc.setFont("helvetica", "bold");
    doc.setFontSize(9.5);
    for (const line of String(value).split("\n")) {
      doc.text(line, LEFT_X, y);
      y += 4.6;
    }
    y += 5.5;
  }

  for (const [title, items] of [[L.kenntnisse, d.kenntnisse], [L.interessen, d.interessen]]) {
    y += 4;
    heading(doc, title, LEFT_X, y);
    y += 9.5;
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9.5);
    for (const item of items) {
      const lines = doc.splitTextToSize(item, LEFT_W - 5);
      doc.text("•", LEFT_X + 0.6, y);
      for (const line of lines) { doc.text(line, LEFT_X + 4.2, y); y += 4.6; }
      y += 1.4;
    }
  }
}

// --- rechte Spalte: fliessender Inhalt ------------------------------------

function makeFlow(doc, d, photoData, L) {
  let y = CONTENT_TOP;
  let section = null;          // laufender Abschnitt, für die Wiederholung
  const newPage = () => {
    doc.addPage();
    background(doc);
    photo(doc, photoData);
    header(doc, d);
    sidebar(doc, d, L);
    y = CONTENT_TOP;
    // Überschrift auf der Folgeseite wiederholen — sonst stehen dort
    // Aufzählungen ohne erkennbaren Zusammenhang.
    if (section) { heading(doc, section, RIGHT_X, y); y += 9; }
  };
  return {
    get y() { return y; },
    need(mm) { if (y + mm > BOTTOM) newPage(); },
    add(mm) { y += mm; },
    heading(text) {
      section = text;
      // Platz für Überschrift UND erste Inhaltszeilen reservieren. Mit nur
      // 24mm passte die Überschrift gerade noch ans Seitenende, der Inhalt
      // brach um — und die Wiederholungslogik setzte sie oben erneut. Ergebnis
      // war eine verwaiste Dopplung.
      this.need(36);
      heading(doc, text, RIGHT_X, y);
      y += 9;
    },
    endSection() { section = null; },
    body(text, size = 8.5, gap = 4.1) {
      doc.setFont("helvetica", "normal");
      doc.setFontSize(size);
      doc.setTextColor(...INK);
      for (const line of doc.splitTextToSize(text.toUpperCase(), RIGHT_W)) {
        this.need(gap);
        doc.text(line, RIGHT_X, y);
        y += gap;
      }
    },
    strong(text, size = 8.5, gap = 4.1) {
      doc.setFont("helvetica", "bold");
      doc.setFontSize(size);
      for (const line of doc.splitTextToSize(text.toUpperCase(), RIGHT_W)) {
        this.need(gap);
        doc.text(line, RIGHT_X, y);
        y += gap;
      }
    },
    bullets(items, size = 8, gap = 4.0) {
      doc.setFont("helvetica", "normal");
      doc.setFontSize(size);
      for (const item of items) {
        const lines = doc.splitTextToSize(item.toUpperCase(), RIGHT_W - 6);
        this.need(gap);
        doc.text("•", RIGHT_X + 1.5, y);
        for (const line of lines) { this.need(gap); doc.text(line, RIGHT_X + 5.5, y); y += gap; }
      }
    },
  };
}

// --- Hauptlauf ------------------------------------------------------------

const [, , dataPath, outPath] = process.argv;
if (!dataPath || !outPath) {
  console.log("Aufruf: node render-cv-allgemein.mjs <daten.json> <ausgabe.pdf>");
  process.exit(1);
}
const d = JSON.parse(readFileSync(dataPath, "utf8"));

// Sektionsbeschriftungen sind überschreibbar, damit derselbe Renderer auch
// englische Bewerbungen erzeugt. Ohne Angabe bleibt alles deutsch.
const L = {
  persoenlichA: "Persönliche", persoenlichB: "Daten",
  kenntnisse: "Kenntnisse", interessen: "Interessen",
  profil: "Profil", kernkompetenzen: "Kernkompetenzen",
  erfahrungen: "Bisherige Erfahrungen",
  ausbildung: "Ausbildung & Weiterbildung",
  zertifikate: "Zertifikate & Schwerpunkte",
  ...(d.labels ?? {}),
};

const photoData = d.foto ? loadPhoto(resolve(dirname(dataPath), d.foto)) : null;

const doc = new jsPDF({ unit: "mm", format: "a4", compress: true });
const FONT = installDisplayFont(doc)
  ? { display: DISPLAY, displayStyle: "normal" }
  : { display: "helvetica", displayStyle: "bold" };
if (FONT.display === "helvetica") {
  console.warn("Hinweis: Arial Black nicht ladbar — Ersatz Helvetica Bold.");
}
background(doc);
photo(doc, photoData);
header(doc, d);
sidebar(doc, d, L);

const f = makeFlow(doc, d, photoData, L);

if (d.profil?.length) {
  f.heading(L.profil);
  for (const p of d.profil) { f.body(p); f.add(3.4); }
  f.add(4);
  f.endSection();
}
if (d.kernkompetenzen?.length) {
  f.heading(L.kernkompetenzen);
  for (const b of d.kernkompetenzen) { f.strong(b.titel); f.body(b.inhalt); f.add(2.2); }
  f.add(4);
  f.endSection();
}
if (d.erfahrungen?.length) {
  f.heading(L.erfahrungen);
  for (const e of d.erfahrungen) {
    f.need(26);
    f.strong(`${e.zeitraum} – ${e.rolle} | ${e.firma}`);
    if (e.untertitel) f.strong(e.untertitel);
    f.bullets(e.bullets ?? []);
    f.add(4.5);
  }
  f.endSection();
}
for (const [key, title] of [["ausbildung", L.ausbildung], ["zertifikate", L.zertifikate]]) {
  if (!d[key]?.length) continue;
  f.add(2);
  f.heading(title);
  f.bullets(d[key]);
  f.add(3);
  f.endSection();
}

mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, Buffer.from(doc.output("arraybuffer")));
console.log(`${outPath} — ${doc.getNumberOfPages()} Seite(n)`);
