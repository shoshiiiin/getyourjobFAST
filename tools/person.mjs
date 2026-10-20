// Zugriff auf profil/person.json für die Renderer.
// Access to profil/person.json for the PDF renderers.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const WURZEL = join(dirname(fileURLToPath(import.meta.url)), "..");

let zwischenspeicher = null;

export function person() {
  if (zwischenspeicher) return zwischenspeicher;
  const pfad = join(WURZEL, "profil", "person.json");
  try {
    zwischenspeicher = JSON.parse(readFileSync(pfad, "utf8"));
  } catch (e) {
    throw new Error(
      `profil/person.json nicht lesbar (${e.message}).\n` +
        "Lege sie an mit: tools/.venv/bin/python tools/einrichten.py",
    );
  }
  return zwischenspeicher;
}

// Längste Kontaktzeile — daraus leiten die Renderer die Schriftgröße ab,
// damit die Zeile unabhängig von der Länge der eigenen Adresse passt.
export function laengsteKontaktzeile(kontakt) {
  const zeilen = (kontakt ?? []).flatMap((r) => (Array.isArray(r) ? r : [r]));
  return zeilen.reduce((a, b) => (b.length > a.length ? b : a), "").toUpperCase() || "BEISPIEL@EXAMPLE.COM";
}
