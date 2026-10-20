#!/usr/bin/env node
/**
 * Rendert eine gespeicherte Stellenanzeige (stelle.md) als lesbares PDF.
 *
 *   node render-stelle.mjs <stelle.md> <ausgabe.pdf>
 *   node render-stelle.mjs --alle          # alle stellen/<ordner>/stelle.md
 *
 * Bewusst schlicht gehalten: Das ist ein Referenzdokument zum Nachlesen,
 * kein Bewerbungsdokument. Kopfzeile mit Metadaten, dann der Anzeigentext.
 */

import { readFileSync, writeFileSync, readdirSync, existsSync } from "node:fs";
import { dirname, join, basename } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const { jsPDF } = await import("jspdf");

const PAGE_W = 210, PAGE_H = 297, MARGIN = 20;
const BREITE = PAGE_W - MARGIN * 2;
const UNTEN = PAGE_H - 18;
const PERI = [198, 204, 255];
const INK = [17, 17, 17];
const GRAU = [110, 110, 120];

// jsPDF-Standardfonts können nur WinAnsi — alles andere würde als Müll
// gerendert. Die Anzeigentexte kommen aus fremdem HTML, deshalb hier
// grosszügiger ersetzen als bei den eigenen Dokumenten.
const ERSATZ = {
  "→": "->", "←": "<-", "↔": "/", "⇒": "=>", "•": "-", "‣": "-", "▪": "-",
  "≥": ">=", "≤": "<=", "–": "-", "—": "-", "…": "...", "★": "*", "✓": "-",
  " ": " ", "‑": "-", "​": "", "﻿": "",
};
const CP1252 = "€‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”•–—˜™š›œžŸ";
function sauber(s) {
  let out = "";
  for (const ch of s) {
    const c = ch.codePointAt(0);
    if (c <= 0x7f || (c >= 0xa0 && c <= 0xff) || CP1252.includes(ch)) { out += ch; continue; }
    out += ch in ERSATZ ? ERSATZ[ch] : " ";
  }
  return out;
}

function parse(md) {
  const zeilen = md.split("\n");
  const titel = (zeilen.find((l) => l.startsWith("# ")) ?? "").slice(2).trim();
  const kopf = (zeilen.find((l) => l.startsWith("**")) ?? "").replace(/\*\*/g, "").trim();
  const meta = [];
  for (const l of zeilen) {
    const m = l.match(/^\|\s*([^|]+?)\s*\|\s*(.+?)\s*\|$/);
    if (m && !/^-+$/.test(m[1]) && m[1] !== "") meta.push([m[1], m[2]]);
  }
  const i = zeilen.findIndex((l) => /^##\s+Anzeige im Volltext/i.test(l));
  const text = i === -1 ? md : zeilen.slice(i + 1).join("\n");
  return { titel, kopf, meta, text: text.trim() };
}

function render(mdPfad, ausgabe) {
  const { titel, kopf, meta, text } = parse(readFileSync(mdPfad, "utf8"));
  const doc = new jsPDF({ unit: "mm", format: "a4", compress: true });
  let y = MARGIN;

  const umbruch = (braucht) => {
    if (y + braucht > UNTEN) { doc.addPage(); y = MARGIN; return true; }
    return false;
  };

  // Kopfbalken
  doc.setFillColor(...PERI);
  doc.rect(0, 0, PAGE_W, 4, "F");
  y = MARGIN + 2;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(17);
  doc.setTextColor(...INK);
  for (const l of doc.splitTextToSize(sauber(titel), BREITE)) { doc.text(l, MARGIN, y); y += 7.4; }

  if (kopf) {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10.5);
    doc.setTextColor(...GRAU);
    y += 1;
    for (const l of doc.splitTextToSize(sauber(kopf), BREITE)) { doc.text(l, MARGIN, y); y += 5; }
  }

  // Metadaten
  if (meta.length) {
    y += 3;
    doc.setDrawColor(...PERI); doc.setLineWidth(0.6);
    doc.line(MARGIN, y, PAGE_W - MARGIN, y);
    y += 5.5;
    doc.setFontSize(8.6);
    for (const [k, v] of meta) {
      umbruch(5);
      doc.setFont("helvetica", "bold"); doc.setTextColor(...INK);
      doc.text(sauber(k), MARGIN, y);
      doc.setFont("helvetica", "normal"); doc.setTextColor(...GRAU);
      for (const l of doc.splitTextToSize(sauber(v), BREITE - 32)) {
        doc.text(l, MARGIN + 30, y); y += 4.3;
      }
    }
    y += 1.5;
    doc.setDrawColor(210, 210, 220); doc.setLineWidth(0.3);
    doc.line(MARGIN, y, PAGE_W - MARGIN, y);
    y += 7;
  }

  // Anzeigentext
  //
  // Die Texte stammen aus JSON-LD und haben fast durchgehend ein führendes
  // Leerzeichen — Einrückung taugt also nicht zur Gliederung. Verlässlich ist
  // der Doppelpunkt am Zeilenende: er markiert in Stellenanzeigen praktisch
  // immer eine Zwischenüberschrift. Kurze Zeilen, die allein zwischen zwei
  // Leerzeilen stehen, sind Einzelangaben (Ort, Vertragsart) — kein Listenpunkt.
  doc.setTextColor(...INK);
  const rohzeilen = text.split("\n");
  for (let idx = 0; idx < rohzeilen.length; idx++) {
    const roh = rohzeilen[idx];
    const zeile = sauber(roh.replace(/\s+$/, ""));
    const inhalt = zeile.trim();
    if (!inhalt) { y += 2.6; continue; }

    const davorLeer = idx === 0 || !rohzeilen[idx - 1].trim();
    const danachLeer = idx === rohzeilen.length - 1 || !rohzeilen[idx + 1].trim();
    const ueberschrift = inhalt.endsWith(":") && inhalt.length < 85;
    const einzeln = !ueberschrift && davorLeer && danachLeer && inhalt.length < 70;
    const fliesstext = !ueberschrift && !einzeln
      && roh.length - roh.trimStart().length === 0;
    const listenpunkt = !ueberschrift && !einzeln && !fliesstext;
    doc.setFont("helvetica", ueberschrift || einzeln ? "bold" : "normal");
    doc.setFontSize(ueberschrift ? 10.8 : einzeln ? 9.6 : 9.4);
    const einzug = listenpunkt ? 4 : 0;
    const teile = doc.splitTextToSize(zeile.trim(), BREITE - einzug);
    if (ueberschrift) { umbruch(14); y += 3.4; }
    else if (einzeln) y += 1.4;
    for (let i = 0; i < teile.length; i++) {
      umbruch(4.6);
      if (listenpunkt && i === 0) doc.text("-", MARGIN, y);
      doc.text(teile[i], MARGIN + einzug, y);
      y += ueberschrift ? 5.4 : 4.5;
    }
    if (ueberschrift) y += 1.8;
    else if (einzeln) y += 1.2;
  }

  // Fusszeilen
  const seiten = doc.getNumberOfPages();
  for (let s = 1; s <= seiten; s++) {
    doc.setPage(s);
    doc.setFont("helvetica", "normal"); doc.setFontSize(7.6);
    doc.setTextColor(...GRAU);
    doc.text(sauber(titel).slice(0, 78), MARGIN, PAGE_H - 10);
    doc.text(`${s} / ${seiten}`, PAGE_W - MARGIN, PAGE_H - 10, { align: "right" });
  }

  writeFileSync(ausgabe, Buffer.from(doc.output("arraybuffer")));
  return seiten;
}

const [, , a, b] = process.argv;
if (a === "--alle") {
  const wurzel = join(here, "..", "stellen");
  for (const ordner of readdirSync(wurzel).sort()) {
    const md = join(wurzel, ordner, "stelle.md");
    if (!existsSync(md)) continue;
    const ziel = join(wurzel, ordner, "Stellenanzeige.pdf");
    const n = render(md, ziel);
    console.log(`  ${ordner.padEnd(52)} ${n} Seite(n)`);
  }
} else if (a && b) {
  console.log(`${b} — ${render(a, b)} Seite(n)`);
} else {
  console.log("Aufruf: node render-stelle.mjs <stelle.md> <ausgabe.pdf>  |  --alle");
  process.exit(1);
}
