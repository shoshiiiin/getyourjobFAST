#!/usr/bin/env node
/**
 * Trefferlisten mit Jev vorsortieren, bevor Claude sie liest.
 *
 *   node tools/jev-vorsortieren.mjs stellen/_stepstone.json [--schwelle 2] [--parallel 4]
 *   node tools/jev-vorsortieren.mjs --eichen      Jev gegen die handbewerteten Stellen
 *   node tools/jev-vorsortieren.mjs --bericht     Summe aus dem Hauptbuch
 *
 * Schreibt `<datei>.jev.json` daneben: behaltene Treffer nach Stufe sortiert,
 * die aussortierten knapp mit Titel, Firma, Stufe und URL — nichts verschwindet
 * still. Jeder Lauf landet in `tools/jev/hauptbuch.jsonl`.
 *
 * Der Schlüssel steht als TYPESAFE_API_KEY in `.env.local` dieses Ordners
 * (console.typesafe.ai/keys). Jev sieht `tools/jev/kandidat.json` — ohne Name
 * und Kontakt — und je Treffer Titel, Firma, Ort und bis zu 1.500 Zeichen Text.
 */

import { appendFileSync, existsSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { basename, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  bandOfPassung,
  calibrate,
  fitRequest,
  normalizeHit,
  parsePassung,
  parseStelleMd,
  readAnswer,
  summarize,
} from "./jev/lib.mjs";

const HIER = dirname(fileURLToPath(import.meta.url));
const WURZEL = join(HIER, "..");
const HAUPTBUCH = join(HIER, "jev", "hauptbuch.jsonl");
const ENDPOINT = "https://api.typesafe.ai/v1/systemone";
const TIMEOUT_MS = 15_000;
const WIEDERHOLEN_BEI = new Set([429, 500, 502, 503, 504]);
const PAUSE_VOR_WIEDERHOLUNG_MS = 2_000;

const envDatei = join(WURZEL, ".env.local");
if (existsSync(envDatei)) process.loadEnvFile(envDatei);

function argument(name, vorgabe) {
  const i = process.argv.indexOf(name);
  return i === -1 ? vorgabe : process.argv[i + 1];
}

const schlaf = (ms) => new Promise((r) => setTimeout(r, ms));

function schluessel() {
  const key = process.env.TYPESAFE_API_KEY;
  if (!key) throw new Error("TYPESAFE_API_KEY fehlt — in Bewerbungen/.env.local eintragen (console.typesafe.ai/keys).");
  return key;
}

async function frageJev(request, versuch = 1) {
  const key = schluessel();
  let res;
  try {
    res = await fetch(ENDPOINT, {
      method: "POST",
      headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
      body: JSON.stringify({ model: "jev-latest", ...request }),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch (e) {
    if (versuch === 1) return schlaf(PAUSE_VOR_WIEDERHOLUNG_MS).then(() => frageJev(request, 2));
    throw new Error(`nicht erreichbar: ${e.message}`);
  }
  if (!res.ok) {
    if (versuch === 1 && WIEDERHOLEN_BEI.has(res.status)) {
      await schlaf(PAUSE_VOR_WIEDERHOLUNG_MS);
      return frageJev(request, 2);
    }
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${text.slice(0, 200)}`);
  }
  return readAnswer(await res.json());
}

/** Ein abgelehnter Schlüssel gilt für jede weitere Anfrage genauso — weiterzufragen wäre sinnlos. */
const SCHLUESSEL_ABGELEHNT = /^HTTP (401|403)\b/;

/**
 * Alle Treffer bewerten, `parallel` gleichzeitig. Ein einzelner Fehler hält den
 * Rest nicht an; ein abgelehnter Schlüssel beendet den ganzen Lauf.
 */
async function bewerteAlle(roh, kandidat, parallel) {
  const ergebnisse = new Array(roh.length);
  let naechster = 0;
  let fertig = 0;
  let abbruch = null;
  async function arbeiter() {
    while (naechster < roh.length && !abbruch) {
      const i = naechster++;
      const hit = normalizeHit(roh[i]);
      try {
        ergebnisse[i] = { roh: roh[i], hit, jev: await frageJev(fitRequest(kandidat, hit)) };
      } catch (e) {
        if (SCHLUESSEL_ABGELEHNT.test(e.message)) abbruch = e.message;
        ergebnisse[i] = { roh: roh[i], hit, fehler: e.message };
      }
      fertig += 1;
      if (fertig % 25 === 0 || fertig === roh.length) process.stdout.write(`  ${fertig}/${roh.length}\n`);
    }
  }
  await Promise.all(Array.from({ length: Math.min(parallel, roh.length) }, arbeiter));
  if (abbruch) throw new Error(`Schlüssel abgelehnt, Lauf abgebrochen: ${abbruch}`);
  return ergebnisse;
}

function trefferAus(datei) {
  const daten = JSON.parse(readFileSync(datei, "utf8"));
  const liste = Array.isArray(daten) ? daten : daten.treffer;
  if (!Array.isArray(liste)) throw new Error(`${datei}: weder eine Liste noch ein Objekt mit "treffer"`);
  return liste;
}

function buche(eintrag) {
  appendFileSync(HAUPTBUCH, JSON.stringify({ am: new Date().toISOString(), ...eintrag }) + "\n", "utf8");
}

const kandidat = () => {
  const { _hinweis, ...profil } = JSON.parse(readFileSync(join(HIER, "jev", "kandidat.json"), "utf8"));
  return profil;
};

const prozent = (teil, ganz) => (ganz ? `${Math.round((teil / ganz) * 100)} %` : "–");

async function sortieren(datei) {
  const schwelle = Number(argument("--schwelle", "2"));
  const parallel = Number(argument("--parallel", "4"));
  const roh = trefferAus(datei);
  console.log(`${roh.length} Treffer aus ${datei}, Schwelle Stufe ${schwelle} …`);

  const ergebnisse = await bewerteAlle(roh, kandidat(), parallel);
  const s = summarize(ergebnisse, schwelle);
  if (s.bewertet === 0) throw new Error(`Kein Treffer bewertet, nichts geschrieben. Erster Fehler: ${ergebnisse[0]?.fehler}`);
  const behalten = ergebnisse
    .filter((e) => !e.jev || e.jev.stufe >= schwelle)
    .sort((a, b) => (b.jev?.stufe ?? -1) - (a.jev?.stufe ?? -1) || (b.jev?.sicherheit ?? 0) - (a.jev?.sicherheit ?? 0))
    .map((e) => ({ ...e.roh, jev: e.jev ?? { fehler: e.fehler } }));
  const aussortiert = ergebnisse
    .filter((e) => e.jev && e.jev.stufe < schwelle)
    .map((e) => ({ titel: e.hit.titel, firma: e.hit.firma, stufe: e.jev.stufe, url: e.roh.url ?? "" }));

  const ziel = datei.replace(/\.json$/, "") + ".jev.json";
  const model = ergebnisse.find((e) => e.jev)?.jev.model ?? "keins";
  writeFileSync(ziel, JSON.stringify({ quelle: basename(datei), model, zusammenfassung: s, behalten, aussortiert }, null, 2), "utf8");
  buche({ modus: "sortieren", datei: basename(datei), model, ...s });

  console.log(`\nJe Stufe 0–4: ${s.jeStufe.join(" · ")}   Fehler: ${s.fehler}`);
  console.log(`Behalten ${s.behalten}, aussortiert ${s.aussortiert} (${prozent(s.aussortiert, s.gesamt)})`);
  console.log(`Nicht mehr zu lesen: ${s.zeichenAussortiert.toLocaleString("de-DE")} Zeichen ≈ ${Math.round(s.zeichenAussortiert / 4).toLocaleString("de-DE")} Tokens (Zeichen ÷ 4, geschätzt)`);
  console.log(`Jev: ${s.jevInputTokens.toLocaleString("de-DE")} Eingabe-Tokens, ${s.jevUsd.toFixed(4)} $`);
  console.log(`→ ${ziel}`);
}

/** Die handbewerteten Stellen: je Ordner stelle.md + analyse.md, dazu die zwei Trefferlisten mit `passung`. */
function handbewertet() {
  const paare = [];
  const stellen = join(WURZEL, "stellen");
  for (const ordner of readdirSync(stellen)) {
    const analyse = join(stellen, ordner, "analyse.md");
    const stelle = join(stellen, ordner, "stelle.md");
    if (!existsSync(analyse) || !existsSync(stelle)) continue;
    const passung = parsePassung(readFileSync(analyse, "utf8"));
    if (passung !== null) paare.push({ quelle: ordner, roh: parseStelleMd(readFileSync(stelle, "utf8")), passung });
  }
  for (const liste of ["stellen-remote/_treffer.json", "stellen-international/_treffer.json"]) {
    const datei = join(WURZEL, liste);
    if (!existsSync(datei)) continue;
    for (const roh of trefferAus(datei)) {
      if (typeof roh.passung === "number") paare.push({ quelle: `${liste}: ${roh.firma}`, roh, passung: roh.passung });
    }
  }
  return paare;
}

async function eichen() {
  const faelle = handbewertet();
  console.log(`${faelle.length} handbewertete Stellen …`);
  const ergebnisse = await bewerteAlle(faelle.map((f) => f.roh), kandidat(), Number(argument("--parallel", "4")));
  const paare = [];
  const abweichend = [];
  ergebnisse.forEach((e, i) => {
    if (!e.jev) return;
    const band = bandOfPassung(faelle[i].passung);
    paare.push({ band, stufe: e.jev.stufe });
    if (Math.abs(band - e.jev.stufe) > 1) abweichend.push(`  Passung ${faelle[i].passung} → Jev ${e.jev.stufe}: ${faelle[i].quelle}`);
  });
  const k = calibrate(paare);
  const s = summarize(ergebnisse, 0);
  if (k.n === 0) throw new Error(`Keine Stelle bewertet, nichts gebucht. Erster Fehler: ${ergebnisse[0]?.fehler}`);
  const model = ergebnisse.find((e) => e.jev)?.jev.model ?? "keins";
  buche({ modus: "eichen", model, n: k.n, exakt: k.exakt, aufEineStufe: k.aufEineStufe, fehler: s.fehler, jevInputTokens: s.jevInputTokens, jevUsd: s.jevUsd });

  console.log(`\nModell ${model}, ${k.n} bewertet, ${s.fehler} Fehler`);
  console.log(`Exakt gleiche Stufe: ${k.exakt}/${k.n} (${prozent(k.exakt, k.n)})`);
  console.log(`Höchstens eine Stufe daneben: ${k.aufEineStufe}/${k.n} (${prozent(k.aufEineStufe, k.n)})`);
  console.log("Zeilen = Handbewertung, Spalten = Jev (Stufe 0–4):");
  k.matrix.forEach((zeile, band) => console.log(`  ${band}: ${zeile.map((n) => String(n).padStart(3)).join("")}`));
  if (abweichend.length) console.log(`Mehr als eine Stufe daneben:\n${abweichend.join("\n")}`);
  console.log(`Jev: ${s.jevInputTokens.toLocaleString("de-DE")} Eingabe-Tokens, ${s.jevUsd.toFixed(4)} $`);
}

function bericht() {
  if (!existsSync(HAUPTBUCH)) return console.log("Noch kein Lauf im Hauptbuch.");
  const eintraege = readFileSync(HAUPTBUCH, "utf8").trim().split("\n").map((z) => JSON.parse(z));
  const laeufe = eintraege.filter((e) => e.modus === "sortieren");
  const summe = (feld) => laeufe.reduce((n, e) => n + (e[feld] ?? 0), 0);
  const letzteEichung = eintraege.filter((e) => e.modus === "eichen").at(-1);
  console.log(`${laeufe.length} Sortierläufe, ${summe("gesamt")} Treffer, ${summe("aussortiert")} aussortiert`);
  console.log(`Nicht mehr zu lesen: ${summe("zeichenAussortiert").toLocaleString("de-DE")} Zeichen ≈ ${Math.round(summe("zeichenAussortiert") / 4).toLocaleString("de-DE")} Tokens (geschätzt)`);
  console.log(`Jev gesamt: ${eintraege.reduce((n, e) => n + (e.jevInputTokens ?? 0), 0).toLocaleString("de-DE")} Tokens, ${eintraege.reduce((n, e) => n + (e.jevUsd ?? 0), 0).toFixed(4)} $`);
  console.log(
    letzteEichung
      ? `Letzte Eichung ${letzteEichung.am.slice(0, 10)}: exakt ${letzteEichung.exakt}/${letzteEichung.n}, ±1 ${letzteEichung.aufEineStufe}/${letzteEichung.n}`
      : "Noch nicht geeicht — erst `--eichen`, dann der Schwelle trauen.",
  );
}

try {
  if (process.argv.includes("--bericht")) bericht();
  else if (process.argv.includes("--eichen")) schluessel() && (await eichen());
  else if (process.argv[2] && !process.argv[2].startsWith("--")) schluessel() && (await sortieren(process.argv[2]));
  else console.log("Aufruf: node tools/jev-vorsortieren.mjs <treffer.json> | --eichen | --bericht");
} catch (e) {
  console.error(e.message);
  process.exitCode = 1;
}
