#!/usr/bin/env node
/**
 * Stellensuche über kostenlose Quellen ohne API-Key.
 *
 *   node jobs-suchen.mjs [ausgabe.json]
 *
 * Quellen: Arbeitsagentur (offizielle Jobbörse) und Arbeitnow (Remote-Fokus EU).
 * Die Suchbegriffe und Orte kommen aus suchprofil.json; Ausschlussbegriffe
 * filtern Ausbildung, Werkstudenten und Praktika direkt weg.
 */

import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const profil = JSON.parse(readFileSync(join(here, "suchprofil.json"), "utf8"));

const schlaf = (ms) => new Promise((r) => setTimeout(r, ms));

function passtNicht(text) {
  const t = text.toLowerCase();
  return profil.ausschluss.some((w) => {
    const i = t.indexOf(w.toLowerCase());
    if (i === -1) return false;
    const davor = i === 0 ? " " : t[i - 1];
    const danach = i + w.length >= t.length ? " " : t[i + w.length];
    return !/[a-zäöüß0-9]/.test(davor) && !/[a-zäöüß0-9]/.test(danach);
  });
}

async function arbeitsagentur(was, wo) {
  const url = new URL("https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs");
  url.searchParams.set("was", was);
  if (wo) { url.searchParams.set("wo", wo); url.searchParams.set("umkreis", "50"); }
  url.searchParams.set("size", "50");
  url.searchParams.set("page", "1");
  url.searchParams.set("veroeffentlichtseit", "28");
  const res = await fetch(url, {
    headers: { "X-API-KEY": "jobboerse-jobsuche", Accept: "application/json" },
    signal: AbortSignal.timeout(20000),
  });
  if (!res.ok) throw new Error(`Arbeitsagentur ${res.status}`);
  const data = await res.json();
  return (data.stellenangebote ?? []).map((j) => ({
    quelle: "Arbeitsagentur",
    id: j.refnr,
    titel: j.titel ?? j.beruf ?? "",
    firma: j.arbeitgeber ?? "Unbekannt",
    ort: j.arbeitsort?.ort ?? "",
    plz: j.arbeitsort?.plz ?? "",
    eintritt: j.eintrittsdatum ?? "",
    veroeffentlicht: j.aktuelleVeroeffentlichungsdatum ?? "",
    url: j.externeUrl ?? `https://www.arbeitsagentur.de/jobsuche/jobdetail/${encodeURIComponent(j.refnr)}`,
    suchbegriff: was,
  }));
}

async function arbeitnow() {
  const res = await fetch("https://www.arbeitnow.com/api/job-board-api", {
    headers: { Accept: "application/json" },
    signal: AbortSignal.timeout(20000),
  });
  if (!res.ok) throw new Error(`Arbeitnow ${res.status}`);
  const data = await res.json();
  return (data.data ?? []).map((j) => ({
    quelle: "Arbeitnow",
    id: j.slug,
    titel: j.title ?? "",
    firma: j.company_name ?? "Unbekannt",
    ort: j.location ?? "",
    plz: "",
    remote: Boolean(j.remote),
    beschreibung: (j.description ?? "").replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").slice(0, 900),
    veroeffentlicht: j.created_at ? new Date(j.created_at * 1000).toISOString().slice(0, 10) : "",
    url: j.url,
    tags: j.tags ?? [],
  }));
}

const treffer = new Map();
const fehler = [];

function aufnehmen(job) {
  if (!job.titel || passtNicht(`${job.titel} ${job.firma}`)) return;
  const key = job.url.toLowerCase().replace(/[?#].*$/, "").replace(/\/+$/, "");
  if (!treffer.has(key)) treffer.set(key, job);
}

console.log("Arbeitsagentur …");
for (const was of profil.suchbegriffe) {
  for (const wo of [...profil.orte, null]) {
    try {
      const jobs = await arbeitsagentur(was, wo);
      jobs.forEach(aufnehmen);
      process.stdout.write(`  ${was} @ ${wo ?? "bundesweit"}: ${jobs.length}\n`);
    } catch (e) {
      fehler.push(`${was} @ ${wo ?? "bundesweit"}: ${e.message}`);
    }
    await schlaf(250);
  }
}

console.log("Arbeitnow …");
try {
  const alle = await arbeitnow();
  const tokens = profil.suchbegriffe.flatMap((s) => s.toLowerCase().split(/\s+/)).filter((t) => t.length > 3);
  const relevant = alle.filter((j) => {
    const hay = `${j.titel} ${j.beschreibung} ${(j.tags ?? []).join(" ")}`.toLowerCase();
    return tokens.some((t) => hay.includes(t));
  });
  relevant.forEach(aufnehmen);
  console.log(`  ${relevant.length} von ${alle.length} relevant`);
} catch (e) {
  fehler.push(`Arbeitnow: ${e.message}`);
}

const ergebnis = {
  gesucht_am: new Date().toISOString().slice(0, 10),
  suchbegriffe: profil.suchbegriffe,
  orte: profil.orte,
  anzahl: treffer.size,
  fehler,
  treffer: [...treffer.values()],
};
const out = process.argv[2] ?? join(here, "..", "stellen", "_suchlauf.json");
writeFileSync(out, JSON.stringify(ergebnis, null, 2), "utf8");
console.log(`\n${treffer.size} Treffer nach Entdopplung und Filter → ${out}`);
if (fehler.length) console.log(`${fehler.length} Quellenfehler:\n  ` + fehler.join("\n  "));
