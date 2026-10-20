# getyourjob

**Ein Bewerbungssystem, das sucht, prüft und schreibt — und bei dem du auf
„Senden" drückst.**
*A job-application system that searches, checks and writes — you press send.*

[Deutsch](#deutsch) · [English](#english)

---

## Deutsch

Jeden Werktagmorgen laufen die Portale durch. Was zum eigenen Mandat passt,
landet in einem lesbaren Bericht. Sagst du Claude „Bewerbung für Muster GmbH",
entsteht daraus eine Analyse der Anzeige, ein Anschreiben nach deinen
Stilregeln, ein auf die Stelle zugeschnittener Lebenslauf als PDF und ein
Mail-Entwurf. Der Tracker führt Buch, und für die Agentur für Arbeit fällt der
Nachweis der Eigenbemühungen per Knopfdruck ab.

**Zwei Dinge macht das System bewusst nicht:** Es verschickt nichts, und es
erfindet nichts. Jede Zahl in einem Anschreiben muss in `profil/belege.md`
stehen, sonst bricht der Bau ab.

### In fünf Minuten startklar

```bash
git clone https://github.com/shoshiiiin/getyourjobFAST.git
cd getyourjob
```

Dann in Claude Code:

```
/einfuehrung
```

Claude fragt dich nach Beruf, Stadt, Suchradius und Wunschrollen, schreibt
daraus dein Profil und baut zum Schluss eine Probe-Bewerbung, die du ansehen
kannst. Dauert etwa zehn Minuten.

**Ohne Claude Code** geht es genauso:

```bash
/opt/homebrew/bin/python3.11 -m venv tools/.venv
tools/.venv/bin/pip install -r tools/requirements.txt
npm install
tools/.venv/bin/python tools/einrichten.py
```

### Vorher ansehen, was herauskommt

Das Repo bringt eine vollständig durchgespielte Beispielbewerbung mit —
erfundene Person, erfundene Firma. Bauen kannst du sie sofort:

```bash
tools/.venv/bin/python tools/bewerbung.py stellen/2026-10-20-muster-projektmanager-digitalisierung --ohne-tracker
```

Danach liegen `Anschreiben_Alex_Beispiel_MUSTER.pdf` und
`Lebenslauf_Alex_Beispiel_MUSTER.pdf` im Ordner. So sieht das Ergebnis aus,
bevor du eine einzige eigene Zeile geschrieben hast.

### Der tägliche Suchlauf

```bash
tools/.venv/bin/python tools/stellensuche.py --tage 7
```

Quellen sind StepStone im Umkreis deines Orts sowie LinkedIn lokal und remote.
Vorher fliegen raus: Titel, die nicht zum Mandat passen, Personaldienstleister
(`tools/suche/ausschluss.json`), Firmen, bei denen du schon beworben bist, und
alles, was ein früherer Lauf schon gesehen hat.

Der Bericht gruppiert nach Sicherheit der Ortsangabe:

| Gruppe | Bedeutung |
|---|---|
| **A** | Home-Office, im Anzeigentext ausdrücklich zugesagt |
| **B** | Höchstens `umkreis_km` von deinem Ort (Luftlinie) |
| **C** | Remote nur laut LinkedIn-Filter — unzuverlässig, vorher klären |
| **D** | Ort nicht bestimmbar |

Täglich automatisch (Mo–Fr 7:30, macOS):

```bash
tools/launchd/install.sh
```

### Eine Bewerbung bauen

1. **Stelle anlegen** — `tools/.venv/bin/python tools/stelle_anlegen.py <firma>`
   nimmt den jüngsten Suchlauf und legt `stellen/<datum>-<firma>-<rolle>/stelle.md` an.
2. **Analysieren** — Claude recherchiert die Firma und schreibt `analyse.md`:
   Aufgabe wörtlich, Tabelle Anforderung ↔ Beleg ↔ Stärke, Risiken,
   Bewerbungsweg, Frist und eine Zeile „Passung NN von 100".
3. **Entwerfen** — `entwurf.json` mit Brief und Lebenslaufauswahl
   (Format im Kopf von `tools/bewerbung.py`).
4. **Bauen** — `tools/.venv/bin/python tools/bewerbung.py stellen/<ordner>`
   prüft Wortzahl und verbotene Wendungen, rendert beide PDFs und trägt die
   Stelle als „Vorbereitet" in den Tracker ein.
5. **Senden** — von dir, nicht vom System.

### Was wo steht

| Datei | Inhalt |
|---|---|
| `profil/person.json` | **Die einzige Datei mit deinen persönlichen Daten.** Name, Kontakt, Anschrift, Ort, Suchradius |
| `profil/suchmandat.json` | Welche Stellentitel zählen (reguläre Ausdrücke) |
| `profil/mandat.md` | Die Regeln deiner Suche in Worten |
| `profil/belege.md` | **Jede Zahl, die behauptet werden darf.** Fehlt sie hier, kommt sie in kein Dokument |
| `profil/stil.md` | Ton und verbotene Wendungen |
| `profil/master-cv.md` | Die vollständige Laufbahn als Fließtext |
| `profil/lebenslauf-allgemein.json` | Der Lebenslauf als Daten (ohne Identität) |
| `tools/suchprofil.json` | Suchbegriffe für die Portale |

### Umgebungsvariablen

Lege bei Bedarf eine Datei `.env.local` im Projektordner an:

```
TYPESAFE_API_KEY=
```

Optional. Ist der Schlüssel gesetzt, sortiert [Jev](https://typesafe.sh) die
Treffer eines Suchlaufs vor und schreibt `<suchlauf>.jev.json`. Ohne Schlüssel
läuft alles normal weiter, nur ohne Vorsortierung. **Jev ist eine Vorauswahl,
keine Bewertung** — die Passung entsteht weiter in `analyse.md`.

### Voraussetzungen

Python 3.11+, Node 20+, macOS oder Linux. Der automatische Suchlauf per
LaunchAgent und die Display-Schrift (Arial Black) sind macOS-spezifisch; ohne
sie fällt das Layout auf Helvetica zurück.

### Tests

```bash
tools/.venv/bin/python -m unittest discover -s tools/test
node --test tools/jev/lib.test.mjs
```

### Fallstricke

- Das Bewerbungsfoto gehört nach `profil/anlagen/bewerbungsfoto.jpg`
  (JPEG, 675 × 900). Fehlt es, entstehen die PDFs ohne Foto, mit Warnung.
- jsPDF kann nur WinAnsi — Pfeile und mathematische Zeichen vermeiden.
- Das Anschreiben darf nicht auf Seite 2 laufen. Über 230 Wörter bricht der
  Bau ab, und das ist Absicht.

---

## English

Every weekday morning the job boards get scanned. Whatever fits your mandate
lands in a readable report. Tell Claude "application for Muster GmbH" and you
get an analysis of the posting, a cover letter following your own style rules,
a CV tailored to that role as a PDF, and a draft email. A tracker keeps the
books.

**Two things the system deliberately does not do:** it sends nothing, and it
invents nothing. Every number in a cover letter must appear in
`profil/belege.md`, or the build refuses to run.

### Up and running in five minutes

```bash
git clone https://github.com/shoshiiiin/getyourjobFAST.git
cd getyourjob
```

Then in Claude Code:

```
/einfuehrung
```

Claude interviews you about your field, city, search radius and target roles,
writes your profile from the answers, and finishes by building a sample
application you can look at. Takes about ten minutes.

**Without Claude Code** it works the same way:

```bash
python3.11 -m venv tools/.venv
tools/.venv/bin/pip install -r tools/requirements.txt
npm install
tools/.venv/bin/python tools/einrichten.py
```

### See the output first

The repo ships one fully worked example — fictional person, fictional company.
Build it right away:

```bash
tools/.venv/bin/python tools/bewerbung.py stellen/2026-10-20-muster-projektmanager-digitalisierung --ohne-tracker
```

Two PDFs appear in that folder. That is what the output looks like before you
have written a single line of your own.

### A note on language

The system targets the German job market: StepStone, German cover-letter
conventions, and the *Nachweis der Eigenbemühungen* that the German employment
agency asks for. Interface and documentation are bilingual; set
`"sprache": "en"` in a draft to produce an English CV and cover letter from
`profil/lebenslauf-allgemein-en.json`.

### Where things live

| File | Holds |
|---|---|
| `profil/person.json` | **The only file with your personal details.** Name, contact, address, city, search radius |
| `profil/suchmandat.json` | Which job titles count (regular expressions) |
| `profil/mandat.md` | The rules of your search, in prose |
| `profil/belege.md` | **Every number you are allowed to claim.** Not here means not in any document |
| `profil/stil.md` | Tone and banned phrases |
| `profil/master-cv.md` | Full career history in prose |
| `profil/lebenslauf-allgemein.json` | The CV as data (no identity) |
| `tools/suchprofil.json` | Search terms for the job boards |

### Requirements

Python 3.11+, Node 20+, macOS or Linux. The scheduled search (LaunchAgent) and
the display font (Arial Black) are macOS-specific; without them the layout
falls back to Helvetica.

---

## Lizenz · License

MIT. Siehe [LICENSE](LICENSE).

Die Beispielperson „Alex Beispiel", alle Firmen und alle Zahlen in diesem Repo
sind frei erfunden. *The example person, companies and figures are fictional.*
