/**
 * Gemeinsames Design für Lebenslauf und Anschreiben.
 *
 * Geometrie 1:1 aus "Allgemeiner Lebenslauf.pdf" rekonstruiert:
 * Vektorpfade via pdftocairo, Textpositionen via pdftotext -bbox.
 * Alle Masse in mm.
 *
 * Beide Dokumente teilen sich diese Datei, damit ein Bewerbungsset
 * nicht auseinanderläuft, wenn an einer Stelle nachjustiert wird.
 */

import { existsSync, readFileSync } from "node:fs";
import { laengsteKontaktzeile } from "./person.mjs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const { jsPDF } = await import("jspdf");

// --- Farben ---------------------------------------------------------------
export const BG = [250, 250, 250];
export const PERI = [198, 204, 255];
export const INK = [17, 17, 17];

// --- Geometrie ------------------------------------------------------------
export const PAGE_W = 210, PAGE_H = 297;
export const BAND_W = 68.66;
export const LEFT_X = 11.5, LEFT_W = 50;
export const RIGHT_X = 81.3, RIGHT_W = 117.7;
export const RIGHT_END = RIGHT_X + RIGHT_W;
export const NAME_BASE = [31.1, 49.9];
export const CONTACT_BASE = 60.0, CONTACT_GAP = 8.7;
export const CONTENT_TOP = 98.3;
export const SIDEBAR_TOP = 123.5;
export const BOTTOM = 284;

const ARCS_TOP = { r: 56.23, cy: 54.14, cx: [68.66, 124.9], side: "right" };
const ARCS_BOT = { r: 85.1, cy: 212.9, cx: [153.81, 219.36], side: "left" };
const PHOTO = { xl: 4.71, xr: 79.23, ytl: 38.21, ytr: 9.93, ybl: 93.39, ybr: 65.08 };
const PHOTO_ASPECT = 900 / 675;
const K = 0.5522847498;

// Das Original nutzt Agrandir (kommerzielle Canva-Schrift, nicht im System).
// Ersatz für Name und Überschriften: Arial Black — die nächstliegende schwere
// Grotesk, die macOS als eigenständige TTF mitbringt.
const DISPLAY_TTF = "/System/Library/Fonts/Supplemental/Arial Black.ttf";

// Zielbreiten aus dem Original gemessen; daraus werden die Schriftgrößen
// abgeleitet statt geschätzt.
const W_NAME = 99.1;       // längste Namenszeile
const W_HEADING = 64.2;    // "KERNKOMPETENZEN"
const W_CONTACT = 74.0;    // längste Kontaktzeile

/** Neues Dokument samt geladener Display-Schrift. */
export function newDoc() {
  const doc = new jsPDF({ unit: "mm", format: "a4", compress: true });
  let font = { family: "helvetica", style: "bold", embedded: false };
  try {
    doc.addFileToVFS("ArialBlack.ttf", readFileSync(DISPLAY_TTF).toString("base64"));
    doc.addFont("ArialBlack.ttf", "ArialBlack", "normal");
    font = { family: "ArialBlack", style: "normal", embedded: true };
  } catch {
    console.warn("Hinweis: Arial Black nicht ladbar — Ersatz Helvetica Bold.");
  }
  font.headingSize = fitSize(doc, "KERNKOMPETENZEN", W_HEADING, font.family, font.style);
  return { doc, font };
}

/** Schriftgröße so wählen, dass `text` genau `target` mm breit wird. */
export function fitSize(doc, text, target, family, style = "normal", max = 80) {
  doc.setFont(family, style);
  doc.setFontSize(10);
  return Math.min(max, target / (doc.getTextWidth(text) / 10));
}

function halfDisc(doc, cx, cy, r, side) {
  const s = side === "right" ? 1 : -1;
  const k = K * r;
  doc.lines([[s * k, 0, s * r, r - k, s * r, r],
             [0, k, -s * (r - k), r, -s * r, r]],
            cx, cy - r, [1, 1], "F", true);
}

export function background(doc) {
  doc.setFillColor(...BG);
  doc.rect(0, 0, PAGE_W, PAGE_H, "F");
  doc.setFillColor(...PERI);
  for (const cx of ARCS_TOP.cx) halfDisc(doc, cx, ARCS_TOP.cy, ARCS_TOP.r, ARCS_TOP.side);
  for (const cx of ARCS_BOT.cx) halfDisc(doc, cx, ARCS_BOT.cy, ARCS_BOT.r, ARCS_BOT.side);
  doc.rect(0, 0, BAND_W, PAGE_H, "F");
}

/** Lädt ein Bild als Data-URL. Rückgabe `null`, wenn kein Pfad gesetzt ist. */
/**
 * Foto als Data-URL. Fehlt die Datei, entsteht das Dokument ohne Foto —
 * mit Warnung, damit es nicht unbemerkt so verschickt wird.
 */
export function loadPhoto(path) {
  if (!path) return null;
  if (!existsSync(path)) {
    console.warn(`WARNUNG: Foto fehlt (${path}) — Dokument ohne Foto.`);
    return null;
  }
  return `data:image/jpeg;base64,${readFileSync(path).toString("base64")}`;
}

export function photo(doc, dataUrl) {
  if (!dataUrl) return;
  doc.saveGraphicsState();
  doc.moveTo(PHOTO.xr, PHOTO.ybr);
  doc.lineTo(PHOTO.xl, PHOTO.ybl);
  doc.lineTo(PHOTO.xl, PHOTO.ytl);
  doc.lineTo(PHOTO.xr, PHOTO.ytr);
  doc.close();
  doc.clip();
  doc.discardPath();
  const w = PHOTO.xr - PHOTO.xl;
  doc.addImage(dataUrl, "JPEG", PHOTO.xl, 8.0, w, w * PHOTO_ASPECT);
  doc.restoreGraphicsState();
}

export function header(doc, font, d) {
  doc.setTextColor(...INK);
  const [l1, l2] = d.nameLines.map((t) => t.toUpperCase());
  const longest = l1.length >= l2.length ? l1 : l2;
  doc.setFont(font.family, font.style);
  doc.setFontSize(fitSize(doc, longest, W_NAME, font.family, font.style));
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

export function heading(doc, font, text, x, y, size = null) {
  doc.setFont(font.family, font.style);
  doc.setFontSize(size ?? font.headingSize);
  doc.setTextColor(...INK);
  doc.text(text.toUpperCase(), x, y);
}

/** Zeichnet das Grundgerüst einer Seite. */
export function chrome(doc, font, d, photoData) {
  background(doc);
  photo(doc, photoData);
  header(doc, font, d);
}
