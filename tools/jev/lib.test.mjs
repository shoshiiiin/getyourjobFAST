// node --test tools/jev/lib.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  FIT_LEVELS,
  normalizeHit,
  fitRequest,
  levelOf,
  bandOfPassung,
  readAnswer,
  summarize,
  calibrate,
  parseStelleMd,
  parsePassung,
} from "./lib.mjs";

const KANDIDAT = { summary: "AI consultant" };

test("normalizeHit liest beide Schreibweisen der Quellen", () => {
  const stepstone = normalizeHit({ titel: "Projektmanager", firma: "Muster", ort: "Musterstadt", url: "u" });
  assert.deepEqual(stepstone, { titel: "Projektmanager", firma: "Muster", ort: "Musterstadt", text: "" });

  const remote = normalizeHit({ titel: "KI-Integrator", firma: "Sonnenernte", ort: "Remote", modell: "100% remote", kern: "n8n" });
  assert.equal(remote.text, "Work model: 100% remote\nn8n");

  const englisch = normalizeHit({ title: "Engineer", company_name: "X", location: "Berlin", beschreibung: "Text" });
  assert.deepEqual(englisch, { titel: "Engineer", firma: "X", ort: "Berlin", text: "Text" });
});

test("normalizeHit kürzt den Anzeigentext auf eine feste Länge", () => {
  const lang = normalizeHit({ titel: "T", firma: "F", beschreibung: "x".repeat(5000) });
  assert.equal(lang.text.length, 1500);
});

test("fitRequest fragt nach Remote nur, wenn ein Anzeigentext da ist", () => {
  const ohneText = fitRequest(KANDIDAT, normalizeHit({ titel: "T", firma: "F" }));
  assert.deepEqual(Object.keys(ohneText.questions), ["fit"]);
  assert.equal(ohneText.questions.fit.type, "score");
  assert.deepEqual(ohneText.questions.fit.criteria, FIT_LEVELS);
  assert.deepEqual(ohneText.state.candidate, KANDIDAT);
  assert.equal(ohneText.state.job.text, undefined);

  const mitText = fitRequest(KANDIDAT, normalizeHit({ titel: "T", firma: "F", beschreibung: "fully remote" }));
  assert.deepEqual(Object.keys(mitText.questions), ["fit", "remote"]);
  assert.equal(mitText.questions.remote.type, "choice");
  assert.equal(mitText.state.job.text, "fully remote");
});

test("levelOf rundet den Erwartungswert und bleibt in 0 bis 4", () => {
  assert.equal(levelOf(2.4), 2);
  assert.equal(levelOf(2.6), 3);
  assert.equal(levelOf(-1), 0);
  assert.equal(levelOf(9), 4);
});

test("bandOfPassung legt die Skala 1–100 auf dieselben fünf Stufen", () => {
  assert.equal(bandOfPassung(1), 0);
  assert.equal(bandOfPassung(20), 0);
  assert.equal(bandOfPassung(21), 1);
  assert.equal(bandOfPassung(55), 2);
  assert.equal(bandOfPassung(64), 3);
  assert.equal(bandOfPassung(84), 4);
  assert.equal(bandOfPassung(100), 4);
});

test("readAnswer liest Stufe, Sicherheit, Remote und Tokens", () => {
  const antwort = readAnswer({
    model: "jev-1.13.0",
    answers: {
      fit: { type: "score", score: 3.2, confidence: 0.7, probabilities: {} },
      remote: { type: "choice", choice: "fully_remote", confidence: 0.9, probabilities: {} },
    },
    usage: { input_tokens: 420, output_tokens: 0 },
  });
  assert.deepEqual(antwort, { stufe: 3, sicherheit: 0.7, remote: "fully_remote", inputTokens: 420, model: "jev-1.13.0" });
});

test("readAnswer wirft bei falscher Form — eine halbe Antwort ist keine", () => {
  assert.throws(() => readAnswer({ answers: {}, usage: { input_tokens: 1 } }), /fit/);
  assert.throws(() => readAnswer({ answers: { fit: { type: "score", score: "hoch", confidence: 1 } }, usage: { input_tokens: 1 } }), /fit/);
  assert.throws(() => readAnswer({ answers: { fit: { type: "score", score: 2, confidence: 1 } } }), /usage/);
});

test("summarize zählt je Stufe und misst, was Claude nicht mehr lesen muss", () => {
  const ergebnisse = [
    { hit: { titel: "a" }, jev: { stufe: 4, inputTokens: 100 } },
    { hit: { titel: "bb" }, jev: { stufe: 1, inputTokens: 100 } },
    { hit: { titel: "ccc" }, jev: { stufe: 0, inputTokens: 100 } },
    { hit: { titel: "d" }, fehler: "HTTP 500" },
  ];
  const s = summarize(ergebnisse, 2);
  assert.deepEqual(s.jeStufe, [1, 1, 0, 0, 1]);
  assert.equal(s.bewertet, 3);
  assert.equal(s.fehler, 1);
  assert.equal(s.behalten, 2, "Stufe 4 und die unbewertete bleiben");
  assert.equal(s.aussortiert, 2);
  assert.equal(s.zeichenAussortiert, JSON.stringify({ titel: "bb" }).length + JSON.stringify({ titel: "ccc" }).length);
  assert.equal(s.jevInputTokens, 300);
  assert.ok(Math.abs(s.jevUsd - 300 * 0.042e-6) < 1e-12);
});

test("calibrate misst Übereinstimmung exakt und auf eine Stufe genau", () => {
  const k = calibrate([
    { band: 4, stufe: 4 },
    { band: 3, stufe: 4 },
    { band: 2, stufe: 0 },
    { band: 1, stufe: 1 },
  ]);
  assert.equal(k.n, 4);
  assert.equal(k.exakt, 2);
  assert.equal(k.aufEineStufe, 3);
  assert.equal(k.matrix[2][0], 1);
});

test("calibrate ohne Paare sagt n = 0 statt 0 %", () => {
  assert.deepEqual(calibrate([]), { n: 0, exakt: 0, aufEineStufe: 0, matrix: calibrate([]).matrix });
});

test("parseStelleMd liest Titel, Firma, Ort und den Anzeigentext", () => {
  const md = [
    "# Projektmanager (w/m/d)",
    "",
    "**Muster GmbH** · Musterstadt 50667 · FULL_TIME",
    "",
    "| | |",
    "|---|---|",
    "| Quelle | StepStone |",
    "",
    "## Anzeige im Volltext",
    "",
    "Wir suchen jemanden.",
  ].join("\n");
  assert.deepEqual(parseStelleMd(md), {
    titel: "Projektmanager (w/m/d)",
    firma: "Muster GmbH",
    ort: "Musterstadt 50667",
    beschreibung: "Wir suchen jemanden.",
  });
});

test("parsePassung nimmt die erste genannte Passung, sonst null", () => {
  assert.equal(parsePassung("**Passung 55 von 100 — deutlich niedriger"), 55);
  assert.equal(parsePassung("keine Zahl"), null);
});
