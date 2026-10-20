#!/usr/bin/env node
/**
 * Anschreiben im Design des Lebenslaufs.
 *
 *   node render-anschreiben.mjs <daten.json> <ausgabe.pdf>
 *
 * Hintergrund, Foto und Kopf kommen aus design.mjs — dadurch sind
 * Anschreiben und Lebenslauf garantiert ein Set.
 *
 * Aufbau der rechten Spalte: Empfänger → Ort/Datum → Betreff → Anrede →
 * Absätze → optionaler Bullet-Block → Grußformel.
 */

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";

import {
  newDoc, chrome, loadPhoto,
  INK, RIGHT_X, RIGHT_W, RIGHT_END, BOTTOM,
} from "./design.mjs";

// Der große Kopf mit Foto belegt rund 90 mm. Damit bleiben für den Brief
// etwa 195 mm statt der sonst üblichen 230 mm — die Typografie ist deshalb
// bewusst kompakter als in einem klassischen DIN-5008-Brief.
const LETTER_TOP = 84;
const BODY_SIZE = 8.8;
const BODY_LEAD = 4.3;
const PARA_GAP = 2.8;

const [, , dataPath, outPath] = process.argv;
if (!dataPath || !outPath) {
  console.log("Aufruf: node render-anschreiben.mjs <daten.json> <ausgabe.pdf>");
  process.exit(1);
}
const d = JSON.parse(readFileSync(dataPath, "utf8"));
const photoData = d.foto ? loadPhoto(resolve(dirname(dataPath), d.foto)) : null;

const { doc, font } = newDoc();
chrome(doc, font, d, photoData);

let y = LETTER_TOP;

function pageBreak() {
  doc.addPage();
  chrome(doc, font, d, photoData);
  y = LETTER_TOP;
}
function need(mm) { if (y + mm > BOTTOM) pageBreak(); }

function lines(text, { size = BODY_SIZE, style = "normal", lead = BODY_LEAD, x = RIGHT_X, width = RIGHT_W } = {}) {
  doc.setFont("helvetica", style);
  doc.setFontSize(size);
  doc.setTextColor(...INK);
  for (const line of doc.splitTextToSize(text, width)) {
    need(lead);
    doc.text(line, x, y);
    y += lead;
  }
}

// --- Empfänger ------------------------------------------------------------
for (const line of d.empfaenger ?? []) {
  lines(line, { size: 9.3, lead: 4.4 });
}

// --- Ort und Datum, rechtsbündig -----------------------------------------
y += 6;
doc.setFont("helvetica", "normal");
doc.setFontSize(9.3);
doc.text(`${d.ort}, ${d.datum}`, RIGHT_END, y, { align: "right" });
y += 7;

// --- Betreff --------------------------------------------------------------
need(20);
doc.setFont(font.family, font.style);
doc.setFontSize(11.5);
for (const line of doc.splitTextToSize(d.betreff, RIGHT_W)) {
  doc.text(line, RIGHT_X, y);
  y += 6.2;
}
y += 4;

// --- Anrede ---------------------------------------------------------------
lines(d.anrede);
y += PARA_GAP;

// --- Fließtext ------------------------------------------------------------
for (const para of d.absaetze ?? []) {
  lines(para);
  y += PARA_GAP;
}

// --- Optionaler Bullet-Block ---------------------------------------------
// Das Format aus dem elunic-Anschreiben: macht das Angebot greifbar und
// bricht die Textwand auf.
if (d.bulletBlock?.punkte?.length) {
  y += 1.5;
  need(24);
  lines(d.bulletBlock.titel, { style: "bold" });
  y += 1.5;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(BODY_SIZE);
  for (const punkt of d.bulletBlock.punkte) {
    const wrapped = doc.splitTextToSize(punkt, RIGHT_W - 6);
    need(BODY_LEAD);
    doc.text("•", RIGHT_X + 1.5, y);
    for (const line of wrapped) {
      need(BODY_LEAD);
      doc.text(line, RIGHT_X + 5.5, y);
      y += BODY_LEAD;
    }
    y += 0.4;
  }
  y += PARA_GAP;
}

// --- Schluss --------------------------------------------------------------
if (d.schluss) { lines(d.schluss); y += PARA_GAP; }
y += 2;
need(17);
lines(d.gruss ?? "Mit freundlichen Grüßen");
y += 8.5;
doc.setFont(font.family, font.style);
doc.setFontSize(11);
doc.text(d.signatur ?? d.nameLines.join(" "), RIGHT_X, y);

mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, Buffer.from(doc.output("arraybuffer")));
console.log(`${outPath} — ${doc.getNumberOfPages()} Seite(n), Satzspiegel bis ${y.toFixed(0)} von ${BOTTOM} mm` +
  (doc.getNumberOfPages() > 1 ? "\n⚠️ Anschreiben läuft auf Seite 2. Text kürzen — ein Anschreiben gehört auf eine Seite." : ""));
