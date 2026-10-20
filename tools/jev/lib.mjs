/**
 * Jev-Vorsortierung — die reine Hälfte: keine Dateien, kein Netz, keine Uhr.
 *
 * Jev (TypeSafe) ist ein Entscheidungsmodell: Zustand und typisierte Frage
 * hinein, Stufe mit Sicherheit heraus, 0,042 $ je Million Eingabe-Tokens.
 * Es liest Englisch am besten, rechnet und zählt nicht und liest wörtlich —
 * deshalb fragt es hier nur „wie gut passt das?" und „steht vollständiges
 * Home-Office im Text?". Alles andere bleibt Code oder Claude.
 */

export const JEV_USD_PER_INPUT_TOKEN = 0.042 / 1_000_000;

/** Fünf Stufen, 0 bis 4 — dieselben wie im Karrierelotse-Schattenlauf. */
export const FIT_LEVELS = [
  "No fit: different field or seniority, or a role the candidate excludes",
  "Weak fit: some overlap, but core requirements are missing",
  "Partial fit: relevant background, notable gaps in key requirements",
  "Good fit: meets most key requirements and matches the target roles",
  "Excellent fit: matches the target roles, seniority and key requirements closely",
];

const FIT_INSTRUCTIONS =
  "How well does the `job` fit the `candidate`'s experience, skills, target roles and location preference? " +
  "Roles listed under `excluded_roles` are no fit. Judge only the match, not the quality of the job.";

const REMOTE_INSTRUCTIONS =
  "Does the job `text` explicitly promise fully remote work (100% home office)? " +
  "Hybrid, some remote days or 'remote possible' do not count as fully remote.";

const REMOTE_CRITERIA = {
  fully_remote: "The text explicitly promises fully remote work",
  not_fully_remote: "The text describes on-site or hybrid work",
  unclear: "The text does not say",
};

/** So viel Anzeigentext sieht Jev; mehr kostet nur Tokens. */
const TEXT_CHARS = 1500;
const LAST_LEVEL = FIT_LEVELS.length - 1;

const first = (...values) => values.find((v) => typeof v === "string" && v.trim())?.trim() ?? "";

/** Ein Treffer aus irgendeiner Quelle in dieselbe Form. */
export function normalizeHit(raw) {
  const modell = first(raw.modell);
  const inhalt = first(raw.beschreibung, raw.description, raw.kern);
  const text = [modell && `Work model: ${modell}`, inhalt].filter(Boolean).join("\n");
  return {
    titel: first(raw.titel, raw.title),
    firma: first(raw.firma, raw.company_name, raw.company),
    ort: first(raw.ort, raw.location),
    text: text.slice(0, TEXT_CHARS),
  };
}

/** Die Anfrage für einen Treffer. Ohne Anzeigentext gibt es keine Remote-Frage — Jev würde raten. */
export function fitRequest(kandidat, hit) {
  const job = { role: hit.titel, company: hit.firma, location: hit.ort, ...(hit.text ? { text: hit.text } : {}) };
  const questions = { fit: { type: "score", instructions: FIT_INSTRUCTIONS, criteria: FIT_LEVELS } };
  if (hit.text) questions.remote = { type: "choice", instructions: REMOTE_INSTRUCTIONS, criteria: REMOTE_CRITERIA };
  return { state: { candidate: kandidat, job }, questions };
}

/** Gerundet, nicht interpoliert: Aus dem Erwartungswert lässt sich keine Zwischenstufe zurückrechnen. */
export function levelOf(score) {
  return Math.min(LAST_LEVEL, Math.max(0, Math.round(score)));
}

/** Die handbewertete Passung 1–100 auf dieselben fünf Stufen. */
export function bandOfPassung(passung) {
  return Math.min(LAST_LEVEL, Math.max(0, Math.floor((passung - 1) / 20)));
}

const isNumber = (v) => typeof v === "number" && Number.isFinite(v);

/** Die Antwort, geprüft. Fehlt die Stufe oder der Verbrauch, wirft sie. */
export function readAnswer(body) {
  const fit = body?.answers?.fit;
  if (fit?.type !== "score" || !isNumber(fit.score) || !isNumber(fit.confidence)) {
    throw new Error(`Jev-Antwort ohne gültige fit-Stufe: ${JSON.stringify(fit)}`);
  }
  const usage = body.usage;
  if (!isNumber(usage?.input_tokens)) throw new Error("Jev-Antwort ohne usage.input_tokens");
  const remote = body.answers.remote;
  return {
    stufe: levelOf(fit.score),
    sicherheit: fit.confidence,
    ...(remote?.type === "choice" && typeof remote.choice === "string" ? { remote: remote.choice } : {}),
    inputTokens: usage.input_tokens,
    model: typeof body.model === "string" ? body.model : "unbekannt",
  };
}

/**
 * Was der Lauf gebracht hat, nur aus Gemessenem: Zeichen der aussortierten
 * Treffer (die Claude nicht mehr lesen muss) und Jevs eigene Tokens.
 * Unbewertete Treffer bleiben immer drin — ein Fehler sortiert nichts aus.
 */
export function summarize(ergebnisse, schwelle) {
  const jeStufe = FIT_LEVELS.map(() => 0);
  let behalten = 0;
  let zeichenBehalten = 0;
  let zeichenAussortiert = 0;
  let jevInputTokens = 0;
  let fehler = 0;
  for (const e of ergebnisse) {
    const zeichen = JSON.stringify(e.hit).length;
    if (!e.jev) {
      fehler += 1;
      behalten += 1;
      zeichenBehalten += zeichen;
      continue;
    }
    jeStufe[e.jev.stufe] += 1;
    jevInputTokens += e.jev.inputTokens;
    if (e.jev.stufe >= schwelle) {
      behalten += 1;
      zeichenBehalten += zeichen;
    } else {
      zeichenAussortiert += zeichen;
    }
  }
  return {
    gesamt: ergebnisse.length,
    bewertet: ergebnisse.length - fehler,
    fehler,
    jeStufe,
    schwelle,
    behalten,
    aussortiert: ergebnisse.length - behalten,
    zeichenBehalten,
    zeichenAussortiert,
    jevInputTokens,
    jevUsd: jevInputTokens * JEV_USD_PER_INPUT_TOKEN,
  };
}

/** Jevs Stufe gegen die Handbewertung: exakt, auf eine Stufe genau, und wo es abweicht. */
export function calibrate(paare) {
  const matrix = FIT_LEVELS.map(() => FIT_LEVELS.map(() => 0));
  let exakt = 0;
  let aufEineStufe = 0;
  for (const { band, stufe } of paare) {
    matrix[band][stufe] += 1;
    if (band === stufe) exakt += 1;
    if (Math.abs(band - stufe) <= 1) aufEineStufe += 1;
  }
  return { n: paare.length, exakt, aufEineStufe, matrix };
}

/** Eine `stelle.md` aus `stellen/<ordner>/` — Titel, Firma · Ort, Volltext. */
export function parseStelleMd(md) {
  const titel = md.match(/^# (.+)$/m)?.[1]?.trim() ?? "";
  const kopf = md.match(/^\*\*(.+?)\*\*\s*·\s*([^·\n]*)/m);
  const volltext = md.split(/^## Anzeige im Volltext\s*$/m)[1] ?? "";
  return {
    titel,
    firma: kopf?.[1]?.trim() ?? "",
    ort: kopf?.[2]?.trim() ?? "",
    beschreibung: volltext.trim(),
  };
}

/** Die erste „Passung NN" einer `analyse.md`, sonst null. */
export function parsePassung(text) {
  const m = text.match(/Passung\s+(\d{1,3})/);
  return m ? Number(m[1]) : null;
}
